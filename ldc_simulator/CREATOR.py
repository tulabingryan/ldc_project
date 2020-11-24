import numpy as np
import pandas as pd
import json
# import geocoder
import time, datetime
import os,socket
###---Local modules---
import FUNCTIONS
import CLOCK
# import TCL
# import FREEZER
# import CREATOR
# import HOUSE
# import HVAC
# import FREEZER
# import FRIDGE
# import WATERHEATER
# import NNTCL
# import CLOTHESWASHER, CLOTHESDRYER, DISHWASHER
# import DER
# import EVEHICLE
# import STORAGE
# import solar
# import WEATHER
# import METER
# import LOAD

'''
Note: Default site location is 1124 Harvard Ln, Ardmore, Papakura 2582, New Zealand
latitude=-37.0321395, longitude=174.9793777
'''



# def to_yearsecond(start, duration):
#     dt_range = pd.date_range(start=pd.to_datetime(start, unit='s'),
#                             freq='S', periods=duration, tz='UTC')
    
#     dt_range = dt_range.tz_convert('Pacific/Auckland')
#     df_datetime = pd.DataFrame(dt_range, columns=['date_time'])
#     df_datetime.index = pd.DatetimeIndex(df_datetime['date_time'])
#     df_datetime['yearsecond'] = ((df_datetime.index.week - 1) * (3600*24*7)) \
#                         + (df_datetime.index.dayofweek * (3600*24)) \
#                         + (df_datetime.index.hour * 3600) \
#                         + (df_datetime.index.minute * 60) \
#                         + (df_datetime.index.second)
#     return df_datetime['yearsecond'].values[0], df_datetime['yearsecond'].values[-1]

# def get_baseloads(start, duration, padding=3600):
#     '''
#     Get the baseloads from './profiles/baseload.h5' and return a dataframe
#     '''
#     x, y = to_yearsecond(start, duration)
#     with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
#         df = store.select('records', where='index>={} and index<={}'.format(x - padding, y + padding))
#     return df

# df_baseload = get_baseloads(int(time.time()), duration=1)
df_baseload = [f'P{x}' for x in range(1,6)]

# with pd.HDFStore('./profiles/baseload.h5', 'r') as store:
#     df_baseload = store.select('winter')


try:
    ### profiles for non-tcl loads
    with open('./profiles/nntcl.json') as f:
        nntcl = json.load(f)
        list_clothesdryer = list(nntcl['Clothesdryer'])
        list_clotheswasher = list(nntcl['Clotheswasher'])
        list_dishwasher = list(nntcl['Dishwasher'])
    dict_clotheswasher = nntcl['Clotheswasher']
    dict_clothesdryer = nntcl['Clothesdryer']
    dict_dishwasher = nntcl['Dishwasher']


    df_clotheswasher = pd.DataFrame.from_dict(dict_clotheswasher, orient='index').transpose().fillna(0)
    df_clothesdryer = pd.DataFrame.from_dict(dict_clothesdryer, orient='index').transpose().fillna(0)
    df_dishwasher = pd.DataFrame.from_dict(dict_dishwasher, orient='index').transpose().fillna(0)

    df_schedules = pd.read_csv('./specs/schedules.csv')
    list_schedules = list(df_schedules.columns)
    del df_schedules

    df_houseSpecs =  pd.read_csv('./specs/houseSpecs.csv')
    df_heatpumpSpecs = pd.read_csv('./specs/heatpumpSpecs.csv')
    df_heaterSpecs = pd.read_csv('./specs/heaterSpecs.csv')
    df_fridgeSpecs = pd.read_csv('./specs/fridgeSpecs.csv')
    df_freezerSpecs = pd.read_csv('./specs/freezerSpecs.csv')
    df_waterheaterSpecs = pd.read_csv('./specs/waterheaterSpecs.csv')
    df_clotheswasherSpecs = pd.read_csv('./specs/clotheswasherSpecs.csv')
    df_clothesdryerSpecs = pd.read_csv('./specs/clothesdryerSpecs.csv')
    df_dishwasherSpecs = pd.read_csv('./specs/dishwasherSpecs.csv')
    df_evSpecs =  pd.read_csv('./specs/evSpecs.csv')
    df_storageSpecs =  pd.read_csv('./specs/storageSpecs.csv')
    df_solarSpecs = pd.read_csv('./specs/pvSpecs.csv')
    df_windSpecs = pd.read_csv('./specs/windSpecs.csv')


except Exception as e:
    print("Error reading file:", e)



def get_open_port(n_ports):
    # get random open port for multicasting
    # port 10000 is reserved for global microgrid multicast
    # hence it is pre-appended in the list
    # it will not be included as available ports to be used
    # by local multicasting ports
    port_list = []  
    while len(port_list) < n_ports:
        try:
            p = np.random.choice(np.arange(10001, 13000, 1)).astype(int)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("",p))
            s.listen(1)
            port = s.getsockname()[1]
            if port in port_list:
                pass
            else:
                port_list.append(port)
            s.close()
        except Exception as e:
            print("Error in CREATOR get_open_port", e)
    assert len(port_list) == n_ports
    return port_list

def get_open_ip(n_ips):
    # generate n_ip number of ip addresses
    # to be used as multicast ip group within the house
    # '224.0.2.0' is reserved to be used by global multicasting
    # at the microgrid level
    ip_list = ['224.0.2.0']
    while len(ip_list) < n_ips + 1:
        try:
            ip = np.random.choice(np.arange(224,239).astype(int)).astype(str) + '.' \
                + np.random.choice(np.arange(0,255).astype(int)).astype(str) + '.' \
                + np.random.choice(np.arange(2,255).astype(int)).astype(str) + '.' \
                + np.random.choice(np.arange(1,255).astype(int)).astype(str)

            if ip in ip_list:
                pass
            else:
                ip_list.append(ip)

        except Exception as e:
            print("Error in CREATOR get_open_ip", e)
    assert len(ip_list[1:]) == n_ips
    return ip_list[1:]





# # funtions for heating / cooling calculations (rule of thumb)
# #@numba.jit(nopython=True, parallel=True, nogil=True)
# def get_heating_power(floor_area):
#     '''Calculate the heating rate as a function of the floor area using the "rule-of-thumb"
#     Rating is based on the study done by Energy Star: http://www.energystar.gov/index.cfm?c=roomac.pr_properly_sized
#     Input:
#         floor_area = the floor area of a the room [m^2]
#     Output:
#         heating_rate = typical heating rate of the given floor area [W]
    
#     # assumption:
#     # 15 BTU/h/ft^2, typical rating of HVAC heating at places of lower latitude, 
#     # colder places may have 50 to 60 BTU/h/ft^2
#     1/(3.28**2)  # conversion factor from square feet to square meter
#     1/3.412141633 # conversion factor from BTU/h to watts
#     '''
#     return float(floor_area) * (15 * (1/3.412141633))/(1/(3.28**2))  # in Watts






# #@numba.jit(nopython=True, parallel=True, nogil=True)
# def get_cooling_power(floor_area):
#     '''This function calculates the cooling rate based on a given area using the "rule-of-thumb"
#     Input:
#         floor_area = floor are of the room [m^2]
#     Output:
#         cooling = cooling power [W]
#         Note: this is the thermal power requirement,
#         To get the equivalent electrical power, divide this value by the COP

#     rating is based on the study done by Energy Star: 
#     http://www.energystar.gov/index.cfm?c=roomac.pr_properly_sized
#     '''
#     floor_area = float(floor_area)
#     cf1 = 1/(3.28**2)  # conversion factor from square feet to square meter
#     cf2 = 1/3.412141633 # conversion factor from BTU/h to watts
    
#     if  floor_area < (150*cf1):
#         return 5000*cf2
#     elif (150*cf1) <= floor_area < (250*cf1):
#         return 6000*cf2
#     elif (250*cf1) <= floor_area < (300*cf1):
#         return 7000*cf2
#     elif (300*cf1) <= floor_area < (350*cf1):
#         return 8000*cf2
#     elif (350*cf1) <= floor_area < (400*cf1):
#         return 9000*cf2
#     elif (400*cf1) <= floor_area < (450*cf1):
#         return 10000*cf2
#     elif (450*cf1) <= floor_area < (550*cf1):
#         return 12000*cf2
#     elif (550*cf1) <= floor_area < (700*cf1):
#         return 14000*cf2
#     elif (700*cf1) <= floor_area < (1000*cf1):
#         return 18000*cf2
#     elif (1000*cf1) <= floor_area < (1200*cf1):
#         return 21000*cf2
#     elif (1200*cf1) <= floor_area < (1400*cf1):
#         return 23000*cf2
#     elif (1400*cf1) <= floor_area < (1500*cf1):
#         return 24000*cf2
#     elif (1500*cf1) <= floor_area < (2000*cf1):
#         return 30000*cf2
#     elif (2000*cf1) <= floor_area < (2500*cf1):
#         return 34000*cf2
#     elif (2500*cf1) <= floor_area < (3000*cf1):
#         return 38000*cf2
#     elif (3000*cf1) <= floor_area < (3500*cf1):
#         return 42000*cf2
#     else:
#         return 50000*cf2



def get_heating_power(floor_area, ceiling_height, cop):
    ''' Calculate the required heating power (thermal) for a room defined by floor_area and ceiling height
    From http://www.theheatpumpshop.com/pdfs/heating_sizing_chart_guide.pdf
    Based on mitsubishi heat pumps the design "rule of thumb":
    55 W/m^3 for well-insulated houses
    65 W/m^3 for cold/damp house or lots of glass
    In this simulation, 60W/m^3 will be used as an average
    
    Note: COP of heatpumps are tested in either of the three standard outside conditions
    H1(7degC); H2 (2degC); H3(-7degC)
    
    Schedule:
    Morning (7-9): 85%
    Day (9 - 17): 50%
    Evening (17-23): 89%
    Night (23 - 7): 30%
    24H: 27%
    '''
    Q_per_m3 = 60
    Qh = np.multiply(np.multiply(floor_area, ceiling_height), Q_per_m3)
    return np.round(Qh, -2)



def get_cooling_power(floor_area, ceiling_height, cop):
    '''
    Estimate the required cooling power (thermal) 
    For a heatpump, the heat transfer from inside to outside and vice versa 
    is the same for cooling and heating
    '''    
    Qh = get_heating_power(floor_area, ceiling_height, cop)
    W = np.divide(Qh, cop)
    Qc = np.subtract(Qh, W)
    return np.round(Qc, -2)


def create_houseSpecs(n_houses=1, ldc_adoption=1, pv_adoption=0, wind_adoption=0, 
    renew=False, latitude=-36.86667, longitude=174.76667, report=False):
    ''' Create specs for houses
    Input:
        n_houses = number of houses
        ldc_adoption = number of houses with ldc capability
        renew = True if new specifications are required
    Output:
        df_houseSpecs
    '''

    # #---create specs for houses and heatpumps
    # if latitude==None or longitude==None:
    #     try:
    #         latitude, longitude = FUNCTIONS.get_coordinates(query='79 Mullins Road, Ardmore, Papakura, New Zealand', report=False)
    #     except Exception as e:
    #         print("Error in CREATOR", e)
    #         latitude = -36.86667 
    #         longitude = 174.76667
    #         print("Using default coordinate:", latitude, longitude)

    try:
        elevation = FUNCTIONS.get_elevation(latitude, longitude)
    except:
        elevation = 10

    # adjust timezone setting used for runtime
    timezone = 'Pacific/Auckland' #FUNCTIONS.get_timezone(latitude, longitude, timestamp=time.time())
    os.environ['TZ'] = timezone
    time.tzset()



    '''
    fileToWrite = open('./specs/houseSpecs.csv', 'wt')
    writer = csv.writer(fileToWrite)
    writer.writerow(('name', 'floor_area', 'latitude','longitude','elevation','albedo',
        'roof_tilt', 'azimuth', 'aspect_ratio', 'ceiling_height', ''))
    writer.writerow()
    fileToWrite.close()
    '''

    ''' MULTICAST ADDRESSES
    224.0.0.0 - 224.0.0.255         Reserved for special “well-known” multicast addresses.

    224.0.1.0 - 238.255.255.255     Globally-scoped (Internet-wide) multicast addresses.
    239.0.0.0 - 239.255.255.255     Administratively-scoped (local) multicast addresses.

    used in this project are:
    224.0.2.0                       for global microgrid multicast
    224.0.2.1 - 238.255.255.255     for local multicast groups at each house
    PORTS:
    10000                           for global microgrid multicast port
    other random available ports    for local multicast groups at each house
    '''

    caps = [chr(x) for x in range(65, 91)] # list of capital letters
    lows = [chr(x) for x in range(97, 123)] # list of small letters

    try:
        df_houseSpecs =  pd.read_csv('./specs/houseSpecs.csv', header=0)
        if (len(df_houseSpecs.index) < n_houses) or renew: raise Exception
    except Exception as e:
        try:
            df_houseSpecs = pd.DataFrame()
            df_houseSpecs['name'] = ["H" + "%03d" % i for i in range(1, 1+n_houses)]
            df_houseSpecs['house'] = df_houseSpecs['name']
            df_houseSpecs['floor_area'] = FUNCTIONS.populate(n_houses, 50.0, 325.0, 186.)  # [m2] floor areas of houses
            df_houseSpecs.loc[0, 'floor_area'] = 67.99
            df_houseSpecs.loc[1, 'floor_area'] = 11.69
            df_houseSpecs.loc[2, 'floor_area'] = 14.00
            df_houseSpecs.loc[3, 'floor_area'] = 11.37
            df_houseSpecs.loc[4, 'floor_area'] = 19.87
            
            urbanDensity = 0.5 # sum of all house areas / total community area
            totalArea = sum(df_houseSpecs['floor_area']) / urbanDensity  # total geographical area occupied by the houses
            oneSide = totalArea**(0.5)  # assuming the total site area is a square, this is the length of one side
            oneSideDegree = oneSide / 1852.0  # converting the length of one side from meter to degree latitude or longitude

            #---create random data for each HVAC units located close to the main site
            df_houseSpecs['latitude'] = np.random.uniform(low=(latitude - (oneSideDegree / 2.)),high=(latitude + (oneSideDegree / 2.0)),size=n_houses)
            df_houseSpecs['longitude'] = np.random.uniform(low=(longitude - (oneSideDegree / 2.)), high=(longitude + (oneSideDegree / 2.0)), size=n_houses)
            df_houseSpecs['elevation'] = np.clip(np.random.normal(elevation, 1, n_houses), a_min=3, a_max=1000)
            df_houseSpecs['albedo'] = FUNCTIONS.populate(n_houses, 0.1, 0.5, 0.2)

            #---House and HVAC properties---
            df_houseSpecs['roof_tilt'] = FUNCTIONS.populate(n_houses, 30.0, 40.0, 36.0)  # [deg] from horizon
            df_houseSpecs['azimuth'] = np.clip(np.random.normal(180.0, 3.0, n_houses), a_min=120, a_max=240)  # [deg] 0 = South, 180=North, -90=East, +90=West
            df_houseSpecs.loc[0, 'azimuth'] = 0
            df_houseSpecs.loc[1, 'azimuth'] = 180
            df_houseSpecs.loc[2, 'azimuth'] = 180
            df_houseSpecs.loc[3, 'azimuth'] = 0
            df_houseSpecs.loc[4, 'azimuth'] = 0
            
            df_houseSpecs['aspect_ratio'] = FUNCTIONS.populate(n_houses, 0.9 * 1.5, 1.1 * 1.5, 1.5)  # 1.5 
            
            df_houseSpecs['ceiling_height'] = 2.4 #FUNCTIONS.populate(n_houses, 0.9 * 2.5, 1.1 * 2.5, 2.5)  # 3.
            df_houseSpecs.loc[0,'ceiling_height'] = 2.4
            df_houseSpecs.loc[1,'ceiling_height'] = 2.4
            df_houseSpecs.loc[2,'ceiling_height'] = 2.4
            df_houseSpecs.loc[3,'ceiling_height'] = 2.4
            df_houseSpecs.loc[4,'ceiling_height'] = 2.4
            
            
            df_houseSpecs['ratio_window_wall'] = FUNCTIONS.populate(n_houses, 0.9 * 0.15, 1.1 * 0.15, 0.15)  # 0.15 
            df_houseSpecs.loc[0, 'ratio_window_wall'] = ((5*0.6*1) + (7*0.6*1.4) + (5*0.6*1) + (2*0.6*1) + (4*0.6*1.4)) / (2.4*(9.520+10.375+7.785+7.785))
            df_houseSpecs.loc[1, 'ratio_window_wall'] = ((3*0.6*1.4) + (1*0.6*1)) / (2.4*(3.2+3.2+3.655+3.655))
            df_houseSpecs.loc[2, 'ratio_window_wall'] = ((6*0.6*1)) / (2.4*((2*(9.715-3.2-1.99)) + (2*2.599)))
            df_houseSpecs.loc[3, 'ratio_window_wall'] = ((3*0.6*1) + (2*0.6*1.4)) / (2.4*(3.2 + 3.2 + 2.960 + 2.960))
            df_houseSpecs.loc[4, 'ratio_window_wall'] = ((8*0.6*1.4)) / (2.4*(4.570 + 5.445 + 2.665 + 3.650))

            df_houseSpecs['ratio_window_roof'] = FUNCTIONS.populate(n_houses, 0.0, 0.10, 0.0)  # 0.00 
            df_houseSpecs.loc[0, 'ratio_window_roof'] = 0
            df_houseSpecs.loc[1, 'ratio_window_roof'] = 0
            df_houseSpecs.loc[2, 'ratio_window_roof'] = 0
            df_houseSpecs.loc[3, 'ratio_window_roof'] = 0
            df_houseSpecs.loc[4, 'ratio_window_roof'] = 0

            df_houseSpecs['roof_area'] = [a / np.cos(b * np.pi/180) for a, b in zip(df_houseSpecs['floor_area'], df_houseSpecs['roof_tilt'])]
            df_houseSpecs['wall_area'] = [(a**0.2) * b * 4 for a, b in zip(df_houseSpecs['floor_area'], df_houseSpecs['ceiling_height'])]
            df_houseSpecs['window_area'] = [a * b for a,b in zip(df_houseSpecs['wall_area'], df_houseSpecs['ratio_window_wall'])]
            df_houseSpecs['skylight_area'] = [a * b for a,b in zip(df_houseSpecs['roof_area'], df_houseSpecs['ratio_window_roof'])]
            '''
            New zealand R values [m^2*degC/Watt]
                    Z1      Z2      Z3
            Roof    R-2.9   R-2.9   R-3.3
            Wall    R-1.9   R-1.9   R-2.0
            Floor   R-1.3   R-1.3   R-1.3
            Glazing (vertical)  R-0.26  R-0.26  R-0.26
            Glazing (skylights) R-0.26  R-0.26  R-0.31

            Australian R Values
                    NSW          Others
            Roof    R-6.3        R-4.1
            Wall    R-3.8        R-2.9
            source: https://www.designnavigator.solutions/CRC.php
            '''
            df_houseSpecs['coefficient_window_transmission'] = FUNCTIONS.populate(n_houses, 0.9 * 0.5, 1.1 * 0.5, 0.5)  # 0.5
            df_houseSpecs['glazing_shgc'] = FUNCTIONS.populate(n_houses, 0.9 * 0.5, 1.1 * 0.5, 0.5)  # 0.5
            df_houseSpecs['R_roof'] = FUNCTIONS.populate(n_houses, 2.9, 3.3, 3.3)  # [m²°C/W]    30.
            df_houseSpecs['R_floor'] = FUNCTIONS.populate(n_houses, 1.3, 1.4, 1.3)  # [m²°C/W]    22.
            df_houseSpecs['R_wall'] = FUNCTIONS.populate(n_houses, 1.9, 2.0, 2.0)  # [m²°C/W]    22.
            df_houseSpecs['R_window'] = FUNCTIONS.populate(n_houses, 0.26, 0.27, 0.26) #[m²°C/W]    20. 
            df_houseSpecs['R_skylight'] = FUNCTIONS.populate(n_houses, 0.26, 0.31, 0.26) #[m²°C/W]    20. 
            df_houseSpecs['mass_fraction_external_heat'] = FUNCTIONS.populate(n_houses,0.3,0.7,0.5)
            df_houseSpecs['mass_fraction_internal_heat'] = FUNCTIONS.populate(n_houses,0.3,0.7,0.5)
            df_houseSpecs['coefficient_internal_surface'] = FUNCTIONS.populate(n_houses,0.3,0.7,0.5)
            df_houseSpecs['thermal_mass_per_area'] = FUNCTIONS.populate(n_houses,0.9,1.1, 1) * 415296  # J/K m^2
            df_houseSpecs['mass_change'] = FUNCTIONS.populate(n_houses, 1, 4, 2.5)  # number of times the air inside the room is replaced in an hour

            df_houseSpecs['temp_max'] = np.random.normal(24, 0.01, n_houses ) #np.random.choice(np.arange(25.0, 26.0, 0.1), replace=True, size=n_houses) # [degC]
            df_houseSpecs['temp_min'] = np.random.normal(20, 0.01, n_houses ) #np.random.choice(np.arange(19.0, 20.0, 0.1), replace=True, size=n_houses) # [degC]

            #--Air and water quality--
            df_houseSpecs['air_density'] = FUNCTIONS.populate(n_houses, 0.99, 1.01, 1.0) * 1.225  # kg/m^3      (0.0735 = from rongxin's data)
            df_houseSpecs['air_heat_capacity'] = FUNCTIONS.populate(n_houses, 0.99, 1.01, 1) * 1000 # J/kg K     (0.2402 = from rongxin's data)
            df_houseSpecs['water_density'] = FUNCTIONS.populate(n_houses, 0.99, 1.01, 1.0) * 1000  # kg/m^3      
            
            df_houseSpecs['installed_lights'] = df_houseSpecs['floor_area'] * np.random.uniform(8., 13.5) # assuming 0.75 - 1.25 W / ft^2 or 8 - 13.5 W/m^2 for lighting
            df_houseSpecs['installed_appliance'] = df_houseSpecs['floor_area'] * np.random.uniform(8.,24.)  # assuming 8-24 watts per m^2 of power for appliances
            df_houseSpecs['utilization'] = FUNCTIONS.populate(n_houses,0.10, 0.30, 0.20) # assuming utilization factor for lights and appliances of 10 % - 30%
            df_houseSpecs['occupancy'] = np.random.choice([1,2,3,4,5],p=[0.10,0.3,0.3,0.2,0.10],size=n_houses) * np.random.uniform(75.,200.)  # a random selection of number of person in the house and assuming a person releases 75 W - 400 W
            df_houseSpecs['schedule'] = np.random.choice(list_schedules, p=[0.1,0.10,0.4,0.3,0.10], size=n_houses)
            df_houseSpecs.loc[0, 'schedule'] = 'P1'  # house 1
            df_houseSpecs.loc[1, 'schedule'] = 'P2'  # house 2
            df_houseSpecs.loc[2, 'schedule'] = 'P3'  # house 3
            df_houseSpecs.loc[3, 'schedule'] = 'P4'  # house 4
            df_houseSpecs.loc[4, 'schedule'] = 'P5'  # house 5
            
            df_houseSpecs['schedule_skew'] = np.random.randint(-900, 900, n_houses)
            df_houseSpecs['phase'] = 'AN'
            df_houseSpecs['angle'] = 0.0
            df_houseSpecs.loc[np.flatnonzero(df_houseSpecs.index%3==1), 'phase'] = 'BN'
            df_houseSpecs.loc[np.flatnonzero(df_houseSpecs.index%3==1), 'angle'] = 120.0
            df_houseSpecs.loc[np.flatnonzero(df_houseSpecs.index%3==2), 'phase'] = 'CN'
            df_houseSpecs.loc[np.flatnonzero(df_houseSpecs.index%3==2), 'angle'] = -120.0
            # phases for Ardmore houses
            df_houseSpecs.loc[0, 'phase'] = 'AN'  # red
            df_houseSpecs.loc[1, 'phase'] = 'BN'  # yellow
            df_houseSpecs.loc[2, 'phase'] = 'CN'  # blue
            df_houseSpecs.loc[3, 'phase'] = 'BN'  # yellow
            df_houseSpecs.loc[4, 'phase'] = 'CN'  # blue
            



            df_houseSpecs['voltage'] = 230.0
            df_houseSpecs['frequency'] = 50.0

            # multicast group
            df_houseSpecs['mcast_ip_local'] = get_open_ip(n_ips=n_houses)
            df_houseSpecs['mcast_port_local'] = get_open_port(n_ports=n_houses)
            df_houseSpecs['mcast_ip_global'] = '224.0.2.0'
            df_houseSpecs['mcast_port_global'] = 10000

            ### other specs common to all
            for i in range(10):
                df_houseSpecs['s{}'.format(i)] = 0
                df_houseSpecs['e{}'.format(i)] = 24
                # NOTE s0..s9 are starting hours, e0..e9 are ending hours
            df_houseSpecs['load_class'] = 'ntcl'
            df_houseSpecs['load_type'] = 'baseload'
            df_houseSpecs['priority'] = 0
            

            '''
            Household Information
            House, Occupancy, Construction Year, Appliances Owned, Type, Size
            1   ,   2   ,   1975-1980               , 35 , Detached         , 4 bed
            2   ,   4   ,   -                       , 15 , Semi-detached    , 3 bed
            3   ,   2   ,   1988                    , 27 , Detached         , 3 bed
            4   ,   2   ,   1850-1899               , 33 , Detached         , 4 bed
            5   ,   4   ,   1878                    , 44 , Mid-terrace      , 4 bed
            6   ,   2   ,   2005                    , 49 , Detached         , 4 bed
            7   ,   4   ,   1965-1974               , 25 , Detached         , 3 bed  # house 1
            8   ,   2   ,   1966                    , 35 , Detached         , 2 bed
            9   ,   2   ,   1919-1944               , 24 , Detached         , 3 bed  # house 2
            10  ,   4   ,   1919-1944               , 31 , Detached         , 3 bed
            11  ,   1   ,   1945-1964               , 25 , Detached         , 3 bed
            12  ,   3   ,   1991-1995               , 26 , Detached         , 3 bed
            13  ,   4   ,   post 2002               , 28 , Detached         , 4 bed
            15  ,   1   ,   1965-1974               , 19 , Semi-detached    , 3 bed
            16  ,   6   ,   1981-1990               , 48 , Detached         , 5 bed
            17  ,   3   ,   mid 60s                 , 22 , Detached         , 3 bed  # house 3
            18  ,   2   ,   1965-1974               , 34 , Detached         , 3 bed
            19  ,   4   ,   1945-1964               , 26 , Semi-detached    , 3 bed  # house 5
            20  ,   2   ,   1965-1974               , 39 , Detached         , 3 bed  # house 4
            21  ,   4   ,   1981-1990               , 23 , Detached         , 3 bed
            '''

            df_houseSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_houses)
            df_houseSpecs.loc[0, 'profile'] = 'house_7'
            df_houseSpecs.loc[1, 'profile'] = 'house_9'
            df_houseSpecs.loc[2, 'profile'] = 'house_17'
            df_houseSpecs.loc[3, 'profile'] = 'house_20'
            df_houseSpecs.loc[4, 'profile'] = 'house_19'

            df_houseSpecs['skew'] = np.random.randint(15) * 60  # random skew schedules of maximum 15 minutes

            df_houseSpecs['irradiance'] = 0
            df_houseSpecs['irradiance_roof'] = 0
            df_houseSpecs['irradiance_wall1'] = 0
            df_houseSpecs['irradiance_wall2'] = 0
            df_houseSpecs['irradiance_wall3'] = 0
            df_houseSpecs['irradiance_wall4'] = 0
            
            df_houseSpecs['counter'] = np.random.uniform(0, 60, n_houses)
            df_houseSpecs['min_cycletime'] = np.random.uniform(3, 60, n_houses) # [s]
            df_houseSpecs['min_coolingtime'] = np.random.uniform(3, 60, n_houses) # [s]
            df_houseSpecs['min_heatingtime'] = np.random.uniform(3, 60, n_houses) # [s]
            
            df_houseSpecs['min_chargingtime'] = 5
            df_houseSpecs['min_dischargingtime'] = 5
            df_houseSpecs['charging_counter'] = 5
            df_houseSpecs['discharging_counter'] = 5
            df_houseSpecs['ldc'] = 0  # determines if the devices is ldc capable

            df_houseSpecs['proposed_status'] = 1
            df_houseSpecs['actual_status'] = 1
            df_houseSpecs['proposed_demand'] = 0
            df_houseSpecs['actual_demand'] = 0

            df_houseSpecs['isotime'] = datetime.datetime.now().isoformat()
            df_houseSpecs['temp_out'] = 15  #[C] outside temperature
            df_houseSpecs['humidity'] = 0.75  # relative humidity
            df_houseSpecs['windspeed'] = 2.5  #[m/s] wind speed

            ### save specs
            df_houseSpecs.to_csv('./specs/houseSpecs.csv', index=False, mode='w')
            print("Created ./specs/houseSpecs.csv, {} units.".format(n_houses))
        except Exception as e:
            print("Error create houseSpecs:", e)
    if report: print(df_houseSpecs.head(10))

    return df_houseSpecs


'''
New zealand R values [m^2*degC/Watt]
        Z1      Z2      Z3
Roof    R-2.9   R-2.9   R-3.3
Wall    R-1.9   R-1.9   R-2.0
Floor   R-1.3   R-1.3   R-1.3
Glazing (vertical)  R-0.26  R-0.26  R-0.26
Glazing (skylights) R-0.26  R-0.26  R-0.31

Australian R Values
        NSW          Others
Roof    R-6.3        R-4.1
Wall    R-3.8        R-2.9
source: https://www.designnavigator.solutions/CRC.php
'''
'''

Building / Room Air Change Rate
- n -
(1/h)
All spaces in general   min 4
Assembly halls  4 - 6
Attic spaces for cooling    12 - 15
Auditoriums     8 - 15
Bakeries    20 - 30
Banks   4 - 10
Barber Shops    6 - 10
Bars    20 - 30
Beauty Shops    6 - 10
Boiler rooms    15 - 20
Bowling Alleys  10 - 15
Cafeterias  12 - 15
Churches    8 - 15
Classrooms  6 - 20
Club rooms  12
Clubhouses  20 - 30
Cocktail Lounges    20 - 30
Computer Rooms  15 - 20
Court Houses    4 - 10
Dance halls     6 - 9
Dental Centers  8 - 12
Department Stores   6 - 10
Dining Halls    12 -15
Dining rooms (restaurants)  12
Dress Shops     6 - 10
Drug Shops  6 - 10
Engine rooms    4 - 6
Factory buildings, ordinary     2 - 4
Factory buildings, with fumes or moisture   10 - 15
Fire Stations   4 - 10
Foundries   15 - 20
Galvanizing plants  20 - 30
Garages repair  20 - 30
Garages storage     4 - 6
Homes, night cooling    10 - 18
Hospital rooms  4 - 6
Jewelry shops   6 - 10
Kitchens    15 - 60
Laundries   10 - 15
Libraries, public   4
Lunch Rooms     12 -15
Luncheonettes   12 -15
Nightclubs  20 - 30
Machine shops   6 - 12
Malls   6 - 10
Medical Centers     8 - 12
Medical Clinics     8 - 12
Medical Offices     8 - 12
Mills, paper    15 - 20
Mills, textile general buildings    4
Mills, textile dye houses   15 - 20
Municipal Buildings     4 - 10
Museums     12 -15
Offices, public     3
Offices, private    4
Photo dark rooms    10 - 15
Pig houses  6 - 10
Police Stations     4 - 10
Post Offices    4 - 10
Poultry houses  6 - 10
Precision Manufacturing     10 - 50
Pump rooms  5
Residences  1 - 2
Restaurants     8 - 12
Retail  6 - 10
School Classrooms   4 - 12
Shoe Shops  6 - 10
Shopping Centers    6 - 10
Shops, machine  5
Shops, paint    15 - 20
Shops, woodworking  5
Substation, electric    5 - 10
Supermarkets    4 - 10
Swimming pools  20 - 30
Town Halls  4 - 10
Taverns     20 - 30
Theaters    8 - 15
Transformer rooms   10 - 30
Turbine rooms, electric     5 - 10
Warehouses  2
Waiting rooms, public   4
Warehouses  6 - 30
'''

# #---test create_houseSpecs---
# create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=False, report=True)
# #---end test


def create_heatpumpSpecs(n_heatpumps, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specs for Heating Ventilation and Air Conditioning (HVAC)
    Input:
        n_heatpump = number of heatpumps
        ldc_adoption = percent of heatpumps with ldc capability
        df_houseSpecs = specs of the houses with heatpumps
        renew = True if new specs are required
    Output:
        df_heatpumpSpecs = dataframe containing heatpump specs

    '''
    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs['floor_area']))

    #---create specs for heatpumps
    try:
        df_heatpumpSpecs =  pd.read_csv('./specs/heatpumpSpecs.csv', header=0)
        
        if (len(df_heatpumpSpecs)< n_heatpumps) or renew: raise Exception
    except Exception as e:
        df_heatpumpSpecs = pd.DataFrame()
        if n_heatpumps > 0:
            try:
                #---property distribution of heatpumps ---
                df_heatpumpSpecs['house'] = df_houseSpecs['name'].values

                # df_heatpumpSpecs.loc[range(5,len(df_houseSpecs.index)),'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], size=n_heatpumps, replace=False)
                # df_heatpumpSpecs.loc[0, 'house'] = df_houseSpecs.loc[0, 'name']
                # df_heatpumpSpecs.loc[1, 'house'] = df_houseSpecs.loc[1, 'name']
                # df_heatpumpSpecs.loc[2, 'house'] = df_houseSpecs.loc[2, 'name']
                # df_heatpumpSpecs.loc[3, 'house'] = df_houseSpecs.loc[3, 'name']
                # df_heatpumpSpecs.loc[4, 'house'] = df_houseSpecs.loc[4, 'name']

                df_houseSpecs.index = df_houseSpecs['name'].values
                df_heatpumpSpecs['name'] = ['AC' + "%03d" % i for i in range(1, 1+n_heatpumps)]
                df_heatpumpSpecs['with_dr'] = np.random.choice([True, False], n_heatpumps, p=[ldc_adoption, 1-ldc_adoption])
                df_heatpumpSpecs['cop'] = np.clip(np.random.normal(3.5, 0.01, n_heatpumps), a_min=2.5, a_max=5.0)  # cop = HEAT/Work
                #---temperature setpoints--- NOTE: heating_setpoint < cooling setpoint
                df_heatpumpSpecs['heating_setpoint'] = np.random.normal(20, 0.001, n_heatpumps) # [degC]
                df_heatpumpSpecs['cooling_setpoint'] = np.random.normal(20, 0.001, n_heatpumps) # [degC]
                df_heatpumpSpecs['tolerance'] = np.random.normal(1, 0.001, n_heatpumps)  # [degC] deadband (+ or -)
                df_heatpumpSpecs['temp_max'] = np.random.normal(24, 0.001, n_heatpumps) # [degC]
                df_heatpumpSpecs['temp_min'] = np.random.normal(16, 0.001, n_heatpumps) # [degC]

                df_heatpumpSpecs['temp_in'] = np.add(df_heatpumpSpecs['heating_setpoint'].values, np.random.uniform(-2.0, 2.0, n_heatpumps))
                df_heatpumpSpecs['temp_mat'] = np.add(df_heatpumpSpecs['cooling_setpoint'].values, np.random.uniform(-2.0, 2.0, n_heatpumps))
                
                df_heatpumpSpecs['temp_out'] = np.clip(np.random.normal(22, 0.5, n_heatpumps), a_min=10, a_max=26) # [degC]
                df_heatpumpSpecs['proposed_status'] = np.random.choice([0, 1],n_heatpumps,p=[0.99, 0.01])
                df_heatpumpSpecs['actual_status'] = np.random.choice([0, 1],n_heatpumps,p=[0.99, 0.01])
                df_heatpumpSpecs['proposed_demand'] = 0
                df_heatpumpSpecs['actual_demand'] = 0
                df_heatpumpSpecs['mode'] = np.random.choice([0, 1],n_heatpumps,p=[0.5, 0.5])

                #---TCL properties ---      
                floor_factor = np.clip(np.random.normal(0.2,0.1, n_houses), a_min=0.15, a_max=0.5)

                df_heatpumpSpecs['floor_area'] = np.clip(np.multiply(df_houseSpecs['floor_area'].values, floor_factor), a_min=9, a_max=72)
                df_heatpumpSpecs['ceiling_height'] = df_houseSpecs['ceiling_height'].values
                df_heatpumpSpecs['heating_power_thermal'] = get_heating_power(df_heatpumpSpecs['floor_area'].values, df_heatpumpSpecs['ceiling_height'].values, df_heatpumpSpecs['cop'].values) # kW
                df_heatpumpSpecs['cooling_power_thermal'] = get_cooling_power(df_heatpumpSpecs['floor_area'].values, df_heatpumpSpecs['ceiling_height'].values, df_heatpumpSpecs['cop'].values)  # kW
                
                ### update actual values for house 0 to 4
                df_heatpumpSpecs.loc[0, 'floor_area'] = 19.87  #[m2] lounge only,  67.99m2 for total house
                df_heatpumpSpecs.loc[1, 'floor_area'] = 11.69
                df_heatpumpSpecs.loc[2, 'floor_area'] = 14.00
                df_heatpumpSpecs.loc[3, 'floor_area'] = 11.37
                df_heatpumpSpecs.loc[4, 'floor_area'] = 19.87

                df_heatpumpSpecs.loc[0, 'heating_power_thermal'] = 8.0e3  #[W] for lounge heatpump,  16.0e3 for centralized
                df_heatpumpSpecs.loc[1, 'heating_power_thermal'] = 6.0e3
                df_heatpumpSpecs.loc[2, 'heating_power_thermal'] = 6.0e3
                df_heatpumpSpecs.loc[3, 'heating_power_thermal'] = 3.2e3
                df_heatpumpSpecs.loc[4, 'heating_power_thermal'] = 6.0e3

                df_heatpumpSpecs.loc[0, 'cooling_power_thermal'] = 7.1e3  #[W] for lounge, 14.0e3 for centralized
                df_heatpumpSpecs.loc[1, 'cooling_power_thermal'] = 5.0e3
                df_heatpumpSpecs.loc[2, 'cooling_power_thermal'] = 5.0e3
                df_heatpumpSpecs.loc[3, 'cooling_power_thermal'] = 2.5e3
                df_heatpumpSpecs.loc[4, 'cooling_power_thermal'] = 5.0e3

                df_heatpumpSpecs.loc[0, 'cop'] = 3.7  # for lounge,  4.0 for centralized
                df_heatpumpSpecs.loc[1, 'cop'] = 4.2
                df_heatpumpSpecs.loc[2, 'cop'] = 4.2
                df_heatpumpSpecs.loc[3, 'cop'] = 4.9
                df_heatpumpSpecs.loc[4, 'cop'] = 4.2

                df_heatpumpSpecs['heating_power'] = np.round((np.divide(df_heatpumpSpecs['heating_power_thermal'].values, df_heatpumpSpecs['cop'].values)), -2)
                df_heatpumpSpecs['cooling_power'] = np.round((np.divide(df_heatpumpSpecs['cooling_power_thermal'].values, df_heatpumpSpecs['cop'].values)), -2)
                df_heatpumpSpecs['ventilation_power'] = 0 #[floor_area * 1 for floor_area in df_heatpumpSpecs['floor_area']]
                df_heatpumpSpecs['standby_power'] = 0 #FUNCTIONS.populate(n_heatpumps, 0.95, 1.05, 1 ) * 1.8  #[watts]
                
                df_heatpumpSpecs['min_heatingtime'] = np.random.randint(120, 180, n_heatpumps) #np.random.choice(np.arange(2.0, 3.0, 0.1), replace=True, size=n_heatpumps) * 60  # [seconds]
                df_heatpumpSpecs['min_coolingtime'] = df_heatpumpSpecs['min_heatingtime'].values #np.random.choice(np.arange(2.0, 3.0, 0.1), replace=True, size=n_heatpumps) * 60  # [seconds]
                df_heatpumpSpecs['cooling_counter'] = np.random.randint(0, 120, n_heatpumps)
                df_heatpumpSpecs['heating_counter'] = np.random.randint(0, 120, n_heatpumps)
                df_heatpumpSpecs['charging_counter'] = np.random.randint(0, 120, n_heatpumps)
                df_heatpumpSpecs['discharging_counter'] = np.random.randint(0, 120, n_heatpumps)
                
                df_heatpumpSpecs['mass_change'] = df_houseSpecs[['mass_change']].values
                df_heatpumpSpecs['volume'] = [ch * fa for ch, fa in zip(df_houseSpecs['ceiling_height'].values, df_heatpumpSpecs['floor_area'].values)] # [m^3]
                df_heatpumpSpecs['air_part'] = np.random.choice(np.arange(0.5, 0.95, 0.01), size=n_heatpumps)
                df_heatpumpSpecs['material_part'] = np.subtract(1, df_heatpumpSpecs['air_part'].values)

                df_heatpumpSpecs['Ua'] = [(x1/y1) + (x2/y2) + (x3/y3) + (x4/y4) + (x5/y5) for x1,y1,x2,y2,x3,y3,x4,y4,x5,y5 in zip(df_houseSpecs['roof_area'], df_houseSpecs['R_roof'],
                    df_houseSpecs['wall_area'], df_houseSpecs['R_wall'], 
                    df_houseSpecs['floor_area'], df_houseSpecs['R_floor'], 
                    df_houseSpecs['window_area'], df_houseSpecs['R_window'], 
                    df_houseSpecs['skylight_area'], df_houseSpecs['R_skylight'])]

                df_heatpumpSpecs['Ua'] = np.multiply(df_heatpumpSpecs['Ua'].values, np.divide(df_heatpumpSpecs['floor_area'].values, df_houseSpecs['floor_area'].values)) * 1.0 # factor to decrease Um since at most only two walls are exposed outside
                df_heatpumpSpecs['U'] = df_heatpumpSpecs['Ua']  # [W/degC]
                df_heatpumpSpecs['Um'] = df_heatpumpSpecs['Ua'] *5 # [W/degC]

                df_heatpumpSpecs['Ca'] = np.multiply(df_heatpumpSpecs['volume'].values, df_heatpumpSpecs['air_part'].values) * 1006.0 * np.mean(df_houseSpecs['air_density']) * 100 # [m^3][Vair/(Vair+Vmat)][J/kg.degC][kg/m^3][adjustment]
                df_heatpumpSpecs['Cm'] = np.multiply(df_heatpumpSpecs['volume'].values, df_heatpumpSpecs['material_part'].values) * 4180 * 1000 * 300 # [m^3][Vmat/(Vair+Vmat)][J/kg.degC][kg/m^3]  water, tweaks
                df_heatpumpSpecs['Cp'] = 1006.0  # [J/kg.degC]


                # print('Ua', df_heatpumpSpecs['Ua'].mean(), df_heatpumpSpecs['Ua'].std())
                # print('Um', df_heatpumpSpecs['Um'].mean(), df_heatpumpSpecs['Um'].std())
                # print('Ca', df_heatpumpSpecs['Ca'].mean(), df_heatpumpSpecs['Ca'].std())
                # print('Cm', df_heatpumpSpecs['Cm'].mean(), df_heatpumpSpecs['Cm'].std())
                # print('heating_power', df_heatpumpSpecs['heating_power'].mean(), df_heatpumpSpecs['heating_power'].std())
                # print('cooling_power', df_heatpumpSpecs['cooling_power'].mean(), df_heatpumpSpecs['cooling_power'].std())
                # print('ventilation_power', df_heatpumpSpecs['ventilation_power'].mean(), df_heatpumpSpecs['ventilation_power'].std())
                # print('standby_power', df_heatpumpSpecs['standby_power'].mean(), df_heatpumpSpecs['standby_power'].std())
                

                df_heatpumpSpecs['mass_fraction_external_heat'] = df_houseSpecs['mass_fraction_external_heat'].values
                df_heatpumpSpecs['mass_fraction_internal_heat'] = df_houseSpecs['mass_fraction_internal_heat'].values
                df_heatpumpSpecs['schedule'] = df_houseSpecs['schedule'].values
                df_heatpumpSpecs['schedule_skew'] = np.random.randint(-900, 900, n_heatpumps)  # [s]
                df_heatpumpSpecs['phase'] = df_houseSpecs['phase'].values
                df_heatpumpSpecs['voltage'] = df_houseSpecs['voltage'].values
                df_heatpumpSpecs['angle'] = df_houseSpecs['angle'].values
                df_heatpumpSpecs['frequency'] = df_houseSpecs['frequency'].values      
                # multicasting ip and ports
                df_heatpumpSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_heatpumpSpecs['house']]
                df_heatpumpSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_heatpumpSpecs['house']]
                df_heatpumpSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_heatpumpSpecs['house']]
                df_heatpumpSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_heatpumpSpecs['house']]

                ### schedules
                dict_sched = {'morning':[7,9], 'day':[9,17], 'evening':[17,23], 'night':[23,7], '24h':[0,24]}
                s = [np.random.choice(['morning', 'day', 'evening', 'night', '24h'], p=[0.30, 0.18, 0.32, 0.11, 0.09], size=10) for i in range(n_heatpumps)]
                ar_s = []
                ar_e = []
                for i in s:
                    ar_s.append([dict_sched[i[j]][0] for j in range(10)])
                    ar_e.append([dict_sched[i[j]][1] for j in range(10)])
                
                ar_s = np.array(ar_s)
                ar_e = np.array(ar_e)

                for i in range(10):
                    df_heatpumpSpecs['s{}'.format(i)] = 0
                    df_heatpumpSpecs['e{}'.format(i)] = 24
                
                # for i in range(n_heatpumps):
                #     for j in range(10):
                #         df_heatpumpSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                #         df_heatpumpSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]


                df_heatpumpSpecs['connected'] = 1

                ### other specs
                df_heatpumpSpecs['load_class'] = 'tcl'
                df_heatpumpSpecs['load_type']= 'heatpump'
                df_heatpumpSpecs['priority'] = np.random.uniform(20, 80, n_heatpumps)
                
                df_heatpumpSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_heatpumps)
                df_heatpumpSpecs['skew'] = 0
                df_heatpumpSpecs['irradiance'] = 0
                df_heatpumpSpecs['irradiance_roof'] = 0
                df_heatpumpSpecs['irradiance_wall1'] = 0
                df_heatpumpSpecs['irradiance_wall2'] = 0
                df_heatpumpSpecs['irradiance_wall3'] = 0
                df_heatpumpSpecs['irradiance_wall4'] = 0
                
                df_heatpumpSpecs['counter'] = np.random.uniform(0, 120, n_heatpumps)
                df_heatpumpSpecs['min_cycletime']= np.random.uniform(30, 120, n_heatpumps)
                df_heatpumpSpecs['min_coolingtime']= np.random.uniform(30, 60, n_heatpumps)
                df_heatpumpSpecs['min_heatingtime']= np.random.uniform(30, 60, n_heatpumps)
                
                df_heatpumpSpecs['min_chargingtime'] = 5
                df_heatpumpSpecs['min_dischargingtime'] = 5
                df_heatpumpSpecs['charging_counter'] = 5
                df_heatpumpSpecs['discharging_counter'] = 5

                ### save specs
                df_heatpumpSpecs.to_csv('./specs/heatpumpSpecs.csv', index=False, mode='w')
                print("Created ./specs/heatpumpSpecs.csv, {} units.".format(n_heatpumps))
                df_houseSpecs.reset_index(drop=True, inplace=True)
            except Exception as e:
                print("error create heatpumpSpecs:",e)
    if report: print(df_heatpumpSpecs.head(10))
    return df_heatpumpSpecs

# ### --- test create_heatpumpSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_heatpumpSpecs(n_heatpumps=20, ldc_adoption=1, df_houseSpecs=df_houseSpecs, renew=True, report=True)
# ### end test



def create_freezerSpecs(n_freezers, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specs for freezers
    Input:
        n_freezer = number of freezers
        ldc_adoption = percent of freezers with ldc capability
        df_houseSpecs = specs of the houses with freezers
        renew = True if new specs are required
    Output:
        df_freezerSpecs = dataframe containing freezer specs

    '''
    # common freezers in the market {volume[liter]:power[Watts]}
    FREEZER_CHOICES = { 90:{'power':[60]}, 
                        118:{'power':[72]}, 
                        138:{'power':[72]}, 
                        188:{'power':[72]},
                        238:{'power':[80]}, 
                        318:{'power':[80]}}  

    #---house indices and probabilities
    houses_idx = df_houseSpecs.index 
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for freezers
    try:
        df_freezerSpecs =  pd.read_csv('./specs/freezerSpecs.csv', header=0)
        if (len(df_freezerSpecs) < n_freezers) or renew: raise Exception
    except Exception as e:
        df_freezerSpecs = pd.DataFrame()
        if n_freezers > 0:
            #---property distribution of freezers ---
            for i in range(n_freezers):
                if i < len(df_houseSpecs.index):
                    df_freezerSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_freezerSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            
            df_freezerSpecs['name'] = ['FZ' + "%03d" % i for i in range(1, 1+n_freezers)]
            df_freezerSpecs['type'] = 'FREEZER'
            df_freezerSpecs['volume'] = np.random.choice([90,118,138,188,238,318],n_freezers,p=[0.2,0.2,0.2,0.2,0.1,0.1]) # [liter], to be used as key for freezer_choices
            df_freezerSpecs['cooling_power'] = np.nan
            
            for i in range(n_freezers): 
                df_freezerSpecs.loc[i,'cooling_power'] = np.random.choice(FREEZER_CHOICES[df_freezerSpecs.loc[i,'volume']]['power'])  # [watts]
            
            df_houseSpecs.index = df_houseSpecs['name'].values
            df_freezerSpecs['volume'] = df_freezerSpecs['volume'] / 1000.0 # [m^3] converted to m^3, 1m^3 = 1000L
            df_freezerSpecs['air_part'] = np.random.choice(np.arange(0.8, 0.95, 0.01), size=n_freezers)  # ratio of heat supplied directly to air
            df_freezerSpecs['material_part'] = np.subtract(1, df_freezerSpecs['air_part'].values)  # ratio of heat supplied directly to materials

            df_freezerSpecs['min_coolingtime'] = np.random.randint(60, 180, n_freezers) #FUNCTIONS.populate(n_freezers,2,2.1,2) *60.0  #[seconds] minimum ON time period of compressor
            df_freezerSpecs['min_heatingtime'] = np.random.randint(10, 60*15, n_freezers) #FUNCTIONS.populate(n_freezers,15,30,15) *60.0  # [seconds] maxtime period for defrosting
            df_freezerSpecs['cooling_counter'] = np.random.randint(0, 60, n_freezers) #[s]
            df_freezerSpecs['heating_counter'] = np.random.randint(0, 60*15, n_freezers)  #[s]
            df_freezerSpecs['charging_counter'] = np.random.randint(0, 120, n_freezers)  #[s]
            df_freezerSpecs['discharging_counter'] = np.random.randint(0, 120, n_freezers)  #[s]
            
            df_freezerSpecs['defrost_cycle'] = np.random.randint(6, 24, n_freezers) * 3600  # [seconds] hours is converted to seconds
            df_freezerSpecs['heating_power'] = FUNCTIONS.populate(n_freezers,300.0,600.0,500.0)  #[watts] for defrosting
            df_freezerSpecs['ventilation_power'] = FUNCTIONS.populate(n_freezers,2.0,5.0,5.0)  #[watts]  
            df_freezerSpecs['standby_power'] = FUNCTIONS.populate(n_freezers,0.3, 0.6, 0.5)  #[watts]  
            df_freezerSpecs['cop'] = np.clip(np.random.normal(4.0, 0.01, n_freezers), a_min=2.5, a_max=4.5) # cop = HEAT/Work
            df_freezerSpecs['cooling_power_thermal'] = np.multiply(df_freezerSpecs['cooling_power'].values, df_freezerSpecs['cop'].values)

            df_freezerSpecs['cooling_setpoint'] = np.random.normal(-10, 0.001, n_freezers) # [degC]
            df_freezerSpecs['heating_setpoint'] = -99999  # [degC] heating mode is disabled
            df_freezerSpecs['tolerance'] = np.random.normal(0.5, 0.001, n_freezers)  # [degC] deadband (+ or -)
            df_freezerSpecs['temp_max'] = np.random.normal(-5, 0.001, n_freezers)  # [degC]
            df_freezerSpecs['temp_min'] = np.random.normal(-20, 0.001, n_freezers)  # [degC]

            df_freezerSpecs['temp_in'] = np.add(df_freezerSpecs['cooling_setpoint'].values, np.random.uniform(-2.0,2.0,n_freezers)) #FUNCTIONS.populate(n_freezers,-15,-10,-10)  # [degC]
            df_freezerSpecs['temp_mat'] = np.add(df_freezerSpecs['cooling_setpoint'].values, np.random.uniform(-2.0,2.0,n_freezers)) # [degC]
            df_freezerSpecs['temp_out'] = np.random.normal(20, 0.001, n_freezers) # [degC] 
            df_freezerSpecs['proposed_status'] = np.random.choice([0, 1],n_freezers,p=[0.9, 0.1])
            df_freezerSpecs['actual_status'] = np.random.choice([0, 1],n_freezers,p=[0.9, 0.1])
            df_freezerSpecs['proposed_demand'] = 0
            df_freezerSpecs['actual_demand'] = 0

            df_freezerSpecs['mode'] = np.random.choice([0, 1],n_freezers,p=[0.5, 0.5])
            df_freezerSpecs['priority'] = np.random.uniform(20,80,n_freezers)
            
            df_freezerSpecs['R_value'] = np.clip(np.random.normal(12.0,1, n_freezers), a_min=5.0, a_max=15.0) / 5.68 # [m²°C/W], 5.68 is the conversion factor from IP to SI units {14.29, 28.57, 42.86, 57.14}
            df_freezerSpecs['surface_area'] = np.multiply(np.power(df_freezerSpecs['volume'].values, 2/3), 6)  # ['m^2'], s = 6*a^2
            df_freezerSpecs['Ua'] = np.divide(df_freezerSpecs['surface_area'], df_freezerSpecs['R_value']) #df_freezerSpecs['volume'] * 1 * 2.27  # [W/degC]
            df_freezerSpecs['U'] = np.divide(df_freezerSpecs['surface_area'], df_freezerSpecs['R_value']*4) #df_freezerSpecs['volume'] * 1 * 2.27  # [W/degC]
            df_freezerSpecs['Um'] = np.divide(df_freezerSpecs['surface_area'], 66.67)  # [W/degC]
            df_freezerSpecs['Ca'] = df_freezerSpecs['volume'] * 0.2 * 1006.0 * np.mean(df_houseSpecs['air_density']) * 3000 # [m^3][Vair/V][717.1J/kg.degC][kg/m^3] [factor]
            df_freezerSpecs['Cm'] = df_freezerSpecs['volume'] * 0.8 * 4180 * 1000 * 3000# [m^3][Vmat/V][J/kg.degC][kg/m^3] [factor]  water
            df_freezerSpecs['Cp'] = 1006.0  # [J/kg.degC]

            
            
            df_freezerSpecs['with_dr'] = np.random.choice([True, False], n_freezers, p=[ldc_adoption, 1-ldc_adoption])
            df_freezerSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['mass_change'] = FUNCTIONS.populate(n_freezers, 0.05, 0.075, 0.065)  # number of times the air inside the room is replaced in an hour
            df_freezerSpecs['schedule'] = df_houseSpecs['schedule'].values
            df_freezerSpecs['schedule_skew'] = np.random.randint(-900, 900, n_freezers)
            # multicasting ip and ports
            df_freezerSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_freezerSpecs['house']]
            df_freezerSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_freezerSpecs['house']]
            
            ### other specs
            for i in range(10):
                df_freezerSpecs['s{}'.format(i)] = 0
                df_freezerSpecs['e{}'.format(i)] = 24
                # NOTE s0..s9 are starting hours, e0..e9 are ending hours
            
            df_freezerSpecs['connected'] = 1
            df_freezerSpecs['load_class'] ='tcl'
            df_freezerSpecs['load_type'] ='freezer'
            
            df_freezerSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_freezers)
            df_freezerSpecs['skew'] = 0
            df_freezerSpecs['irradiance'] = 0
            df_freezerSpecs['irradiance_roof'] = 0
            df_freezerSpecs['irradiance_wall1'] = 0
            df_freezerSpecs['irradiance_wall2'] = 0
            df_freezerSpecs['irradiance_wall3'] = 0
            df_freezerSpecs['irradiance_wall4'] = 0
            
            df_freezerSpecs['counter'] = np.random.uniform(0, 60, n_freezers)
            df_freezerSpecs['min_cycletime'] = np.random.uniform(30, 60, n_freezers)
            df_freezerSpecs['min_coolingtime'] = np.random.uniform(30, 60, n_freezers)
            df_freezerSpecs['min_heatingtime'] = np.random.uniform(30, 60, n_freezers)
            
            df_freezerSpecs['min_chargingtime'] = 5
            df_freezerSpecs['min_dischargingtime'] = 5
            df_freezerSpecs['charging_counter'] = 5
            df_freezerSpecs['discharging_counter'] = 5
            
            
            ### save specs
            df_freezerSpecs.to_csv('./specs/freezerSpecs.csv', index=False, mode='w')
            print("Created ./specs/freezerSpecs.csv, {} units.".format(n_freezers))
            df_houseSpecs.reset_index(drop=True, inplace=True)
    if report: print(df_freezerSpecs.head(10))
    return df_freezerSpecs



### --- test create_freezerSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_freezerSpecs(n_freezers=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
### end test


def create_fridgeSpecs(n_fridges, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create fridge specifications
    Input:
        n_fridges = number of fridges
        ldc_adoption = percent of fridges that are ldc enabled
        df_houseSpecs = dataframe containing house specifications
        renew = True if new specifications are required

    Output:
        df_fridgeSpecs
    '''

    #---property distribution of refr6.3gerators / fridges ---
    FRIDGE_CHOICES={82:{'power':[60]}, 
                76:{'power':[72]}, 
                100:{'power':[72]}, 
                98:{'power':[72]}, 
                116:{'power':[72]}}  # volume[liter]: power[Watts]

    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for refrigerators
    try:
        df_fridgeSpecs = pd.read_csv('./specs/fridgeSpecs.csv')
        if (len(df_fridgeSpecs) < n_fridges) or renew: raise Exception
    except Exception as e:
        df_fridgeSpecs = pd.DataFrame()
        if n_fridges > 0:
            for i in range(n_fridges):
                if i < len(df_houseSpecs.index):
                    df_fridgeSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_fridgeSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
                    

            # df_fridgeSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_fridges)
            
            # df_fridgeSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_fridgeSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_fridgeSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_fridgeSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_fridgeSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']


            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_fridgeSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_fridges)
            df_fridgeSpecs['name'] = ['FG' + "%03d" % i for i in range(1, 1+n_fridges)]         
            df_fridgeSpecs['volume'] = np.random.choice([82,76,100,98,116],n_fridges) # [liter], to be used as key for fridge_choices
            df_fridgeSpecs['cooling_power'] = np.nan
            for i in range(n_fridges): df_fridgeSpecs.loc[i,'cooling_power'] = np.random.choice(FRIDGE_CHOICES[df_fridgeSpecs.loc[i,'volume']]['power'])  # [watts]
            df_fridgeSpecs['volume'] = df_fridgeSpecs['volume'] / 1000.0  # [m^3] converted, 1 m^3 = 1000 liter
            df_fridgeSpecs['air_part'] = np.random.choice(np.arange(0.8, 0.95, 0.01), size=n_fridges)  # ratio of heat supplied directly to air
            df_fridgeSpecs['material_part'] = np.subtract(1, df_fridgeSpecs['air_part'].values)

            df_fridgeSpecs['min_coolingtime'] = np.random.randint(60, 180, n_fridges) #[seconds] minimum ON time period of compressor
            df_fridgeSpecs['min_heatingtime'] = np.random.randint(10, 60*30, n_fridges)  # [seconds] maxtime period for defrosting
            df_fridgeSpecs['cooling_counter'] = np.random.randint(0, 60, n_fridges)
            df_fridgeSpecs['heating_counter'] = np.random.randint(0, 60*15, n_fridges)
            df_fridgeSpecs['charging_counter'] = np.random.randint(0, 120, n_fridges)
            df_fridgeSpecs['discharging_counter'] = np.random.randint(0, 120, n_fridges)
            
            df_fridgeSpecs['defrost_cycle'] = np.random.randint(6, 24, n_fridges) * 3600  # [seconds] hours is converted to seconds
            df_fridgeSpecs['heating_power'] = FUNCTIONS.populate(n_fridges,300.0,600.0,500.0)  #[watts]  for defrosting
            df_fridgeSpecs['ventilation_power'] = FUNCTIONS.populate(n_fridges,2.0,5.0,4.0)  #[watts]  
            df_fridgeSpecs['standby_power'] = FUNCTIONS.populate(n_fridges,0.3, 0.6, 0.5)  #[watts]  
            df_fridgeSpecs['cop'] = np.clip(np.random.normal(4.0, 0.01, n_fridges), a_min=2.5, a_max=4.5) # cop = HEAT/Work
            df_fridgeSpecs['cooling_power_thermal'] = np.multiply(df_fridgeSpecs['cooling_power'].values, df_fridgeSpecs['cop'].values)

            df_fridgeSpecs['cooling_setpoint'] = np.random.normal(4, 0.001, n_fridges)  # [degC]
            df_fridgeSpecs['heating_setpoint'] = -99999  # [degC]  heating is disabled
            df_fridgeSpecs['tolerance'] = np.random.normal(0.5, 0.001, n_fridges)  # [degC] deadband (+ or -)
            df_fridgeSpecs['temp_max'] = np.random.normal(7, 0.001, n_fridges)  # [degC]
            df_fridgeSpecs['temp_min'] = np.random.normal(-4, 0.001, n_fridges)  # [degC]

            df_fridgeSpecs['temp_in'] =  np.add(df_fridgeSpecs['cooling_setpoint'].values, np.random.uniform(-2.0, 2.0, n_fridges)) #FUNCTIONS.populate(n_fridges, 0, 5, 5)  # [degC]
            df_fridgeSpecs['temp_mat'] = np.add(df_fridgeSpecs['cooling_setpoint'].values, np.random.uniform(-2.0, 2.0, n_fridges)) # [degC]
            df_fridgeSpecs['temp_out'] = np.random.normal(20, 0.001, n_fridges) # [degC] 
            df_fridgeSpecs['proposed_status'] = np.random.choice([0, 1],n_fridges,p=[0.9, 0.1])
            df_fridgeSpecs['actual_status'] = np.random.choice([0, 1],n_fridges,p=[0.9, 0.1])
            df_fridgeSpecs['proposed_demand'] = 0
            df_fridgeSpecs['actual_demand'] = 0
            df_fridgeSpecs['mode'] = np.random.choice([0, 1],n_fridges,p=[0.5, 0.5])
            df_fridgeSpecs['priority'] = np.random.uniform(20,80,n_fridges)
            
            df_fridgeSpecs['R_value'] = np.clip(np.random.normal(12.0,1, n_fridges), a_min=5, a_max=15) / 5.68 # [m²°C/W], 5.68 is the conversion factor from IP to SI units
            df_fridgeSpecs['surface_area'] = np.multiply(np.power(df_fridgeSpecs['volume'].values, 2/3), 6)  # ['m^2'], s = 6*a^2
            df_fridgeSpecs['Ua'] = np.divide(df_fridgeSpecs['surface_area'], df_fridgeSpecs['R_value']) #df_fridgeSpecs['volume'] * 1 * 2.27  # [W/degC]
            df_fridgeSpecs['U'] = np.divide(df_fridgeSpecs['surface_area'], df_fridgeSpecs['R_value']*4) #df_fridgeSpecs['volume'] * 1 * 2.27  # [W/degC]
            df_fridgeSpecs['Um'] = np.divide(df_fridgeSpecs['surface_area'], 66.67)  # [W/degC]
            df_fridgeSpecs['Ca'] = df_fridgeSpecs['volume'] * 0.2 * 1006.0 * np.mean(df_houseSpecs['air_density']) * 3000# [m^3] [Vair/V]  [717.1J/kg.degC][kg/m^3] [tweaks]
            df_fridgeSpecs['Cm'] = df_fridgeSpecs['volume'] * 0.8 * 4180 * 1000 * 3000 # [m^3][Vmat/V][J/kg.degC][kg/m^3]  water
            df_fridgeSpecs['Cp'] = 1006.0  # [J/kg.degC]

            #---initial conditions
            df_fridgeSpecs['with_dr'] = np.random.choice([True, False], n_fridges, p=[ldc_adoption, 1-ldc_adoption])
            df_fridgeSpecs['mass_change'] = FUNCTIONS.populate(n_fridges, 0.05, 0.075, 0.065)  # number of times the air inside the room is replaced in an hour
            df_fridgeSpecs['schedule'] = df_houseSpecs['schedule'].values
            df_fridgeSpecs['schedule_skew'] = np.random.randint(-900, 900, n_fridges)
            df_fridgeSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_fridgeSpecs['house']]
            df_fridgeSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_fridgeSpecs['house']]
            df_fridgeSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_fridgeSpecs['house']]
            df_fridgeSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_fridgeSpecs['house']]
            # multicasting ip and ports
            df_fridgeSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_fridgeSpecs['house']]
            df_fridgeSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_fridgeSpecs['house']]
            df_fridgeSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_fridgeSpecs['house']]
            df_fridgeSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_fridgeSpecs['house']]
            
            ### other specs
            for i in range(10):
                df_fridgeSpecs['s{}'.format(i)] = 0
                df_fridgeSpecs['e{}'.format(i)] = 24
                # NOTE s0..s9 are starting hours, e0..e9 are ending hours
            
            df_fridgeSpecs['connected'] = 1
            df_fridgeSpecs['load_class'] ='tcl'
            df_fridgeSpecs['load_type'] ='fridge'
            
            df_fridgeSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_fridges)
            df_fridgeSpecs['skew'] = 0
            df_fridgeSpecs['irradiance'] = 0
            df_fridgeSpecs['irradiance_roof'] = 0
            df_fridgeSpecs['irradiance_wall1'] = 0
            df_fridgeSpecs['irradiance_wall2'] = 0
            df_fridgeSpecs['irradiance_wall3'] = 0
            df_fridgeSpecs['irradiance_wall4'] = 0
            
            df_fridgeSpecs['counter'] = np.random.uniform(0, 60, n_fridges)
            df_fridgeSpecs['min_cycletime'] = np.random.uniform(30, 60, n_fridges)
            df_fridgeSpecs['min_coolingtime'] = np.random.uniform(30, 60, n_fridges)
            df_fridgeSpecs['min_heatingtime'] = np.random.uniform(30, 60, n_fridges)
            
            df_fridgeSpecs['min_chargingtime'] = 5
            df_fridgeSpecs['min_dischargingtime'] = 5
            df_fridgeSpecs['charging_counter'] = 5
            df_fridgeSpecs['discharging_counter'] = 5
            
            ### save specs
            df_fridgeSpecs.to_csv('./specs/fridgeSpecs.csv', index=False, mode='w')
            print("Created ./specs/fridgeSpecs.csv, {} units".format(n_fridges))
            df_houseSpecs.reset_index(drop=True, inplace=True)
    if report: print(df_fridgeSpecs.head(10))
    return df_fridgeSpecs


### --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_fridgeSpecs(n_fridges=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
### end test

'''
    0-14 years: 19.62% (male 457,071 /female 434,789)
    15-24 years: 13.16% (male 307,574 /female 290,771)
    25-54 years: 39.58% (male 902,909 /female 896,398)
    55-64 years: 12.06% (male 266,855 /female 281,507)
    65 years and over: 15.57% (male 327,052 /female 380,701) (2018 est.)
'''

def create_heaterSpecs(n_heaters, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specs for Heating Ventilation and Air Conditioning (HVAC)
    Input:
        n_heater = number of heaters
        ldc_adoption = percent of heaters with ldc capability
        df_houseSpecs = specs of the houses with heaters
        renew = True if new specs are required
    Output:
        df_heaterSpecs = dataframe containing heater specs

    '''
    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs['floor_area']))

    #---create specs for heaters
    try:
        df_heaterSpecs =  pd.read_csv('./specs/heaterSpecs.csv', header=0)
        
        if (len(df_heaterSpecs)< n_heaters) or renew: raise Exception
    except Exception as e:
        df_heaterSpecs = pd.DataFrame()
        if n_heaters > 0:
            try:
                #---property distribution of heaters ---
                df_heaterSpecs['house'] = df_houseSpecs['name'].values

                # df_heaterSpecs.loc[range(5,len(df_houseSpecs.index)),'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], size=n_heaters, replace=False)
                # df_heaterSpecs.loc[0, 'house'] = df_houseSpecs.loc[0, 'name']
                # df_heaterSpecs.loc[1, 'house'] = df_houseSpecs.loc[1, 'name']
                # df_heaterSpecs.loc[2, 'house'] = df_houseSpecs.loc[2, 'name']
                # df_heaterSpecs.loc[3, 'house'] = df_houseSpecs.loc[3, 'name']
                # df_heaterSpecs.loc[4, 'house'] = df_houseSpecs.loc[4, 'name']

                df_houseSpecs.index = df_houseSpecs['name'].values
                df_heaterSpecs['name'] = ['EH' + "%03d" % i for i in range(1, 1+n_heaters)]
                df_heaterSpecs['with_dr'] = np.random.choice([True, False], n_heaters, p=[ldc_adoption, 1-ldc_adoption])
                df_heaterSpecs['cop'] = 1  # cop = HEAT/Work
                #---temperature setpoints--- NOTE: heating_setpoint < cooling setpoint
                df_heaterSpecs['heating_setpoint'] = np.random.normal(20, 0.001, n_heaters)
                df_heaterSpecs['cooling_setpoint'] = 99999
                df_heaterSpecs['tolerance'] = np.random.normal(1, 0.001, n_heaters)  # [degC] deadband (+ or -)
                df_heaterSpecs['temp_max'] = np.random.normal(23, 0.001, n_heaters) # [degC]
                df_heaterSpecs['temp_min'] = np.random.normal(17, 0.001, n_heaters) # [degC]

                df_heaterSpecs['temp_in'] = np.add(df_heaterSpecs['heating_setpoint'].values, np.random.uniform(-2.0, 2.0, n_heaters))
                df_heaterSpecs['temp_mat'] = np.add(df_heaterSpecs['heating_setpoint'].values, np.random.uniform(-2.0, 2.0, n_heaters))
                
                df_heaterSpecs['temp_out'] = np.clip(np.random.normal(22, 0.5, n_heaters), a_min=10, a_max=26) # [degC]
                df_heaterSpecs['proposed_status'] = np.random.choice([0, 1],n_heaters,p=[0.99, 0.01])
                df_heaterSpecs['actual_status'] = np.random.choice([0, 1],n_heaters,p=[0.99, 0.01])
                df_heaterSpecs['proposed_demand'] = 0
                df_heaterSpecs['actual_demand'] = 0

                df_heaterSpecs['mode'] = np.random.choice([0, 1],n_heaters,p=[0.5, 0.5])
                df_heaterSpecs['priority'] = np.random.uniform(20, 80,n_heaters)

                #---TCL properties ---      
                floor_factor = np.clip(np.random.normal(0.2,0.01, n_heaters), a_min=0.1, a_max=0.3)

                df_heaterSpecs['floor_area'] = np.clip(np.multiply(df_houseSpecs['floor_area'].values, floor_factor), a_min=4, a_max=72)
                df_heaterSpecs.loc[0, 'floor_area'] = 67.99
                df_heaterSpecs.loc[1, 'floor_area'] = 11.69
                df_heaterSpecs.loc[2, 'floor_area'] = 14.00
                df_heaterSpecs.loc[3, 'floor_area'] = 11.37
                df_heaterSpecs.loc[4, 'floor_area'] = 19.87
                df_heaterSpecs['ceiling_height'] = df_houseSpecs['ceiling_height'].values
                df_heaterSpecs['heating_power_thermal'] = np.round(df_heaterSpecs['floor_area'].values * 80, -2)
                df_heaterSpecs['heating_power'] = df_heaterSpecs['heating_power_thermal'].values

                df_heaterSpecs.loc[df_heaterSpecs['floor_area']<4, 'heating_power'] = 500
                df_heaterSpecs.loc[((df_heaterSpecs['floor_area']>=4)&(df_heaterSpecs['floor_area']<8)), 'heating_power'] = 1000
                df_heaterSpecs.loc[((df_heaterSpecs['floor_area']>=8)&(df_heaterSpecs['floor_area']<13)), 'heating_power'] = 1500
                df_heaterSpecs.loc[((df_heaterSpecs['floor_area']>=13)&(df_heaterSpecs['floor_area']<17)), 'heating_power'] = 2000
                df_heaterSpecs.loc[((df_heaterSpecs['floor_area']>=17)), 'heating_power'] = 2400

                
                df_heaterSpecs['cooling_power_thermal'] = 0
                df_heaterSpecs['cooling_power'] = 0
                df_heaterSpecs['ventilation_power'] = 0
                df_heaterSpecs['standby_power'] = 0 #FUNCTIONS.populate(n_heaters, 0.95, 1.05, 1 ) * 1.8  #[watts]
                
                df_heaterSpecs['min_heatingtime'] = 0 #np.random.choice(np.arange(2.0, 3.0, 0.1), replace=True, size=n_heaters) * 60  # [seconds]
                df_heaterSpecs['min_coolingtime'] = 0
                df_heaterSpecs['cooling_counter'] = 0
                df_heaterSpecs['heating_counter'] = 0
                df_heaterSpecs['charging_counter'] = np.random.randint(0, 120, n_heaters)
                df_heaterSpecs['discharging_counter'] = np.random.randint(0, 120, n_heaters)
                
                df_heaterSpecs['mass_change'] = df_houseSpecs[['mass_change']].values
                df_heaterSpecs['volume'] = [ch * fa for ch, fa in zip(df_houseSpecs['ceiling_height'].values, df_heaterSpecs['floor_area'].values)] # [m^3]
                df_heaterSpecs['air_part'] = np.random.choice(np.arange(0.5, 0.95, 0.01), size=n_heaters)  # ratio of heat supplied directly to air
                df_heaterSpecs['material_part'] = np.subtract(1, df_heaterSpecs['air_part'].values)

                df_heaterSpecs['Ua'] = [(x1/y1) + (x2/y2) + (x3/y3) + (x4/y4) + (x5/y5) for x1,y1,x2,y2,x3,y3,x4,y4,x5,y5 in zip(df_houseSpecs['roof_area'], df_houseSpecs['R_roof'],
                    df_houseSpecs['wall_area'], df_houseSpecs['R_wall'], 
                    df_houseSpecs['floor_area'], df_houseSpecs['R_floor'], 
                    df_houseSpecs['window_area'], df_houseSpecs['R_window'], 
                    df_houseSpecs['skylight_area'], df_houseSpecs['R_skylight'])]

                df_heaterSpecs['Ua'] = np.multiply(df_heaterSpecs['Ua'].values, np.divide(df_heaterSpecs['floor_area'].values, df_houseSpecs['floor_area'].values)) * 1 # 0.7 factor to decrease Um since at most only two walls are exposed outside
                df_heaterSpecs['U'] = np.divide(df_heaterSpecs['Ua'].values, 8.7) 
                df_heaterSpecs['Um'] = df_heaterSpecs['Ua'] * 5  # [W/degC]
                df_heaterSpecs['Ca'] = np.multiply(df_heaterSpecs['volume'].values, df_heaterSpecs['air_part'].values) * 1006.0 * np.mean(df_houseSpecs['air_density']) * 10 # [m^3][J/kg.degC][kg/m^3][tweak]
                df_heaterSpecs['Cm'] = np.multiply(df_heaterSpecs['volume'].values, df_heaterSpecs['material_part'].values) * 4180 * 1000 * 300 # [m^3][Vmat/Vair][J/kg.degC][kg/m^3][tweak]  
                df_heaterSpecs['Cp'] = 1006.0  # [J/kg.degC]

                df_heaterSpecs['mass_fraction_external_heat'] = df_houseSpecs['mass_fraction_external_heat'].values
                df_heaterSpecs['mass_fraction_internal_heat'] = df_houseSpecs['mass_fraction_internal_heat'].values
                df_heaterSpecs['schedule'] = df_houseSpecs['schedule'].values
                df_heaterSpecs['schedule_skew'] = np.random.randint(-900, 900, n_heaters)
                df_heaterSpecs['phase'] = df_houseSpecs['phase'].values
                df_heaterSpecs['voltage'] = df_houseSpecs['voltage'].values
                df_heaterSpecs['angle'] = df_houseSpecs['angle'].values
                df_heaterSpecs['frequency'] = df_houseSpecs['frequency'].values      
                # multicasting ip and ports
                df_heaterSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_heaterSpecs['house']]
                df_heaterSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_heaterSpecs['house']]
                df_heaterSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_heaterSpecs['house']]
                df_heaterSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_heaterSpecs['house']]

                ### add running schedules
                dict_sched = {'morning':[7,9], 'day':[9,17], 'evening':[17,23], 'night':[23,7], '24h':[0,24]}
                s = [np.random.choice(['morning', 'day', 'evening', 'night', '24h'], p=[0.30, 0.18, 0.32, 0.11, 0.09], size=10) for i in range(n_heaters)]  #p=[0.30, 0.18, 0.32, 0.11, 0.09]
                ar_s = []
                ar_e = []
                for i in s:
                    ar_s.append([dict_sched[i[j]][0] for j in range(10)])
                    ar_e.append([dict_sched[i[j]][1] for j in range(10)])
                
                ar_s = np.array(ar_s)
                ar_e = np.array(ar_e)

                for i in range(10):
                    df_heaterSpecs['s{}'.format(i)] = 0
                    df_heaterSpecs['e{}'.format(i)] = 24
                
                # for i in range(n_heaters):
                #     for j in range(10):
                #         df_heaterSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                #         df_heaterSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]

                df_heaterSpecs['connected'] = 1

                ### other specs
                df_heaterSpecs['load_class'] = 'tcl'
                df_heaterSpecs['load_type']= 'heater'
                df_heaterSpecs['d_priority'] = np.random.uniform(20,80, n_heaters)
                
                df_heaterSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_heaters)
                df_heaterSpecs['skew'] = 0
                df_heaterSpecs['irradiance'] = 0
                df_heaterSpecs['irradiance_roof'] = 0
                df_heaterSpecs['irradiance_wall1'] = 0
                df_heaterSpecs['irradiance_wall2'] = 0
                df_heaterSpecs['irradiance_wall3'] = 0
                df_heaterSpecs['irradiance_wall4'] = 0
                
                df_heaterSpecs['counter'] = np.random.uniform(0, 10, n_heaters)
                df_heaterSpecs['min_cycletime']= np.random.uniform(3, 5, n_heaters)
                df_heaterSpecs['min_coolingtime']= np.random.uniform(3, 5, n_heaters)
                df_heaterSpecs['min_heatingtime']= np.random.uniform(3, 5, n_heaters)
                
                df_heaterSpecs['min_chargingtime'] = 5
                df_heaterSpecs['min_dischargingtime'] = 5
                df_heaterSpecs['charging_counter'] = 5
                df_heaterSpecs['discharging_counter'] = 5

                ### save specs
                df_heaterSpecs.to_csv('./specs/heaterSpecs.csv', index=False, mode='w')
                print("Created ./specs/heaterSpecs.csv, {} units.".format(n_heaters))
                df_houseSpecs.reset_index(drop=True, inplace=True)
            except Exception as e:
                print("error create heaterSpecs:",e)
    if report: print(df_heaterSpecs.head(10))
    return df_heaterSpecs



'''
Thickness:  0.5 in. 1 in.   1.5 in. 2 in.
R-Value:    14.29   28.57   42.86   57.14

5/inch
'''



def create_waterheaterSpecs(n_waterheaters, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create fridge specifications
    Input:
        n_waterheaters = number of waterheaters
        ldc_adoption = percent of devices that are ldc enabled
        df_houseSpecs = dataframe containing house specifications
        renew = True if new specifications are required

    Output:
        df_waterheaterSpecs
    '''
    '''
    Type of building    Consumption per occupant    Peak demand per occupant    Storage per occupant
                            liter/day                   gal/day liter/hr        gal/hr  liter   gal
    Factories (no process)  22 - 45                      5-10      9                2   5   1
    Hospitals, general      160                          35        30               7   27  6
    Hospitals, mental       110                          25        22               5   27  6
    Hostels                 90                           20        45               10  30  7
    Hotels                  90 - 160                     20-35     45               10  30  7
    Houses and flats        90 - 160                     20-35     45               10  30  7
    Offices                 22                           5         9                2   5   1
    Schools, boarding       115                          25        20               4   25  5
    Schools, day            15                           3         9                2   5   1

    '''
    # WATERHEATER_CHOICES={80:{'power':[5500,4500],'diameter':[(26./12),(24./12)],'height':[(60.25/12),(59.25/12)]},
    #                         50:{'power':[5500,4500],'diameter':[(24./12),(22./12),(20./12)],'height':[(47.75/12),(58.5/12),(50./12)]},
    #                         40:{'power':[4500],'diameter':[(22./12),(20./12),(18./12),(20./12)],'height':[(48.25/12),(59./12),(47.25/12)]},
    #                         38:{'power':[4500],'diameter':[(24./12)],'height':[(31.58/12)]},
    #                         30:{'power':[3500],'diameter':[(18./12)],'height':[(45.25/12)]},
    #                         28:{'power':[3500],'diameter':[(22./12)],'height':[(29.5/12)]}} # size in gallon

    WATERHEATER_CHOICES= {
        400:{'power':[3600, 4800]},
        177:{'power':[3000]},
        180:{'power':[2000,3000]},
        # 25:{'power':[2000]},
        # 45:{'power':[3000]},
        # 90:{'power':[3000]},
        135:{'power':[2000, 3000]},
        250:{'power':[3000]},
        300:{'power':[3000, 5000]},


    }

    ### tank dimension is assumed: height = 2*diameter, volume=(2*d)*pi*d^2 / 4 = pi*(d^3)/2, surface area = pi*(2*d^2), 
    ### d = np.power((v*2/pi), 1/3), surface_area = np.pi(2*(np.power((v*2/pi), 2/3)))


    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for water heaters
    try:
        df_waterheaterSpecs = pd.read_csv('./specs/waterheaterSpecs.csv')
        if (len(df_waterheaterSpecs) < n_waterheaters) or renew: raise Exception
    except Exception as e:
        df_waterheaterSpecs = pd.DataFrame()
        if n_waterheaters > 0:
            #---property distribution of waterheaters ---
            for i in range(n_waterheaters):
                if i < len(df_houseSpecs.index):
                    df_waterheaterSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_waterheaterSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            
            # df_waterheaterSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_waterheaters)            
            # df_waterheaterSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_waterheaterSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_waterheaterSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_waterheaterSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_waterheaterSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            
            df_waterheaterSpecs['name'] = ['WH' + "%03d" % i for i in range(1, 1+n_waterheaters)]
            # df_waterheaterSpecs['house_area'] = [df_houseSpecs.loc[]]
            # volume_options = sorted(list(WATERHEATER_CHOICES.keys()))
            df_waterheaterSpecs['volume'] = np.random.choice(list(WATERHEATER_CHOICES),n_waterheaters) # [liter], to be used as key for WATERHEATER_CHOICES
            
            df_waterheaterSpecs.loc[0, 'volume'] = 180  # livability house (west), ardmore
            df_waterheaterSpecs.loc[1, 'volume'] = 400  # East house 1
            df_waterheaterSpecs.loc[2, 'volume'] = 177  # East house 2
            df_waterheaterSpecs.loc[3, 'volume'] = 177  # East house 3
            df_waterheaterSpecs.loc[4, 'volume'] = 177  # East house 4
            df_waterheaterSpecs['heating_power'] = np.nan
            
            for i in range(n_waterheaters): df_waterheaterSpecs.loc[i,'heating_power'] = np.random.choice(WATERHEATER_CHOICES[df_waterheaterSpecs.loc[i,'volume']]['power'])  # [watts]
            # df_waterheaterSpecs['volume'] = df_waterheaterSpecs['volume'] / 264.172 # [gallon], converted, 1m^3 = 264.172 gal
            df_waterheaterSpecs['volume'] = df_waterheaterSpecs['volume'] / 1000 # [liter], converted, 1m^3 = 1000 Liter
            df_waterheaterSpecs['air_part'] = np.ones(n_waterheaters)
            df_waterheaterSpecs['material_part'] = np.subtract(1, df_waterheaterSpecs['air_part'].values)

            df_waterheaterSpecs.loc[0, 'heating_power'] = 2000
            df_waterheaterSpecs.loc[1, 'heating_power'] = 3600
            df_waterheaterSpecs.loc[2, 'heating_power'] = 3000
            df_waterheaterSpecs.loc[3, 'heating_power'] = 3000
            df_waterheaterSpecs.loc[4, 'heating_power'] = 3000
            df_waterheaterSpecs['cooling_power'] = 0  # cooling is disabled
            df_waterheaterSpecs['ventilation_power'] = 0  # no ventilation
            df_waterheaterSpecs['standby_power'] = 0 
            df_waterheaterSpecs['heating_power_thermal'] = df_waterheaterSpecs['heating_power'].values
            df_waterheaterSpecs['cooling_power_thermal'] = df_waterheaterSpecs['cooling_power'].values
            
            df_waterheaterSpecs['min_heatingtime'] = np.random.randint(5*60, 30*60, n_waterheaters) # [seconds] maxtime period for heating
            df_waterheaterSpecs['min_coolingtime'] = 0  # cooling is disabled
            df_waterheaterSpecs['cooling_counter'] = 0
            df_waterheaterSpecs['heating_counter'] = np.random.randint(0, 5*60, n_waterheaters)
            df_waterheaterSpecs['charging_counter'] = np.random.randint(0, 120, n_waterheaters)
            df_waterheaterSpecs['discharging_counter'] = np.random.randint(0, 120, n_waterheaters)
            

            df_waterheaterSpecs['cop'] = np.clip(np.random.normal(0.99, 0.1, n_waterheaters), a_min=0.98, a_max=1.0) # cop = HEAT/Work
            df_waterheaterSpecs['heating_setpoint'] = np.clip(np.random.normal(57, 0.001, size=n_waterheaters).round(1), a_min=57, a_max=57.1)  # [degC]
            df_waterheaterSpecs['cooling_setpoint'] = 99999  # set as infinity to disable cooling
            df_waterheaterSpecs['tolerance'] = np.clip(np.random.normal(4.0, 0.01, n_waterheaters).round(1), a_min=4, a_max=4.5)  # [degC] deadband (+ or -)
            df_waterheaterSpecs['temp_max'] = np.clip(np.random.normal(61, 0.01, n_waterheaters).round(1), a_min=61, a_max=62)  # [degC]
            df_waterheaterSpecs['temp_min'] = np.clip(np.random.normal(53, 0.01, n_waterheaters).round(1), a_min=45, a_max=50) # [degC]

            df_waterheaterSpecs['temp_in'] = np.random.uniform(50,60,n_waterheaters) # [degC] 
            df_waterheaterSpecs['temp_mat'] = df_waterheaterSpecs['temp_in'] # [degC] 
            df_waterheaterSpecs['temp_out'] = np.clip(np.random.normal(20, 0.01, n_waterheaters), a_min=15, a_max=20) # [degC] 
            df_waterheaterSpecs['temp_refill'] = np.clip(np.random.normal(13, 0.5, n_waterheaters), a_min=4, a_max=18) # [degC] 
            df_waterheaterSpecs['proposed_status'] = np.random.choice([0, 1],n_waterheaters,p=[0.99, 0.01])
            df_waterheaterSpecs['actual_status'] = np.random.choice([0, 1],n_waterheaters,p=[0.99, 0.01])
            df_waterheaterSpecs['proposed_demand'] = 0
            df_waterheaterSpecs['actual_demand'] = 0
            df_waterheaterSpecs['mode'] = 1 # heating
            df_waterheaterSpecs['priority'] = np.random.uniform(20,80,n_waterheaters)
            
            df_waterheaterSpecs['R_value'] = np.clip(np.random.normal(7.0, 1, n_waterheaters), a_min=5, a_max=25) / 5.678263337 # [m²°C/W], 5.68 is the conversion factor from °F·ft2·h/BTU, 5 per inch thick of polystyrene
            df_waterheaterSpecs['surface_area'] = np.pi*(2*(np.power((df_waterheaterSpecs['volume']*2/np.pi), 2/3)))  # ['m^2'], 
            
            df_waterheaterSpecs['Ua'] = np.divide(df_waterheaterSpecs['surface_area'], df_waterheaterSpecs['R_value']) # [W/degC]
            df_waterheaterSpecs['Um'] = np.divide(df_waterheaterSpecs['surface_area'], 0.01)  # [W/degC]
            df_waterheaterSpecs['U'] = np.divide(df_waterheaterSpecs['surface_area'], df_waterheaterSpecs['R_value']*5*12)  # [W/degC]
            df_waterheaterSpecs['Ca'] = df_waterheaterSpecs['volume'] * 4186 * np.mean(df_houseSpecs['water_density'])  # [J/degC] 
            df_waterheaterSpecs['Cm'] = df_waterheaterSpecs['surface_area'] * 0.003 * 385 * 8960 # [m^2][thickness, m][J/kg.degC][kg/m^3]  # copper
            df_waterheaterSpecs['Cp'] = 4186  # [J/kg.degC]
            
            df_waterheaterSpecs['location'] = np.random.choice(['inside','outside'],n_waterheaters,p=[0.5,0.5])
            df_waterheaterSpecs['mass_change'] = FUNCTIONS.populate(n_waterheaters,90,160,120)*(1/1000)*(1/(24*3600)) * 3.71 # [m^3] 90 - 160 litres per day per occupant
            df_waterheaterSpecs['schedule'] = df_houseSpecs['schedule'].values
            df_waterheaterSpecs['schedule_skew'] = np.random.randint(-900, 900, n_waterheaters)
            df_waterheaterSpecs['with_dr'] = np.random.choice([True, False], n_waterheaters, p=[ldc_adoption, 1-ldc_adoption])
            df_waterheaterSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_waterheaterSpecs['house']]
            df_waterheaterSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_waterheaterSpecs['house']]
            df_waterheaterSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_waterheaterSpecs['house']]
            df_waterheaterSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_waterheaterSpecs['house']]
            # multicasting ip and ports
            df_waterheaterSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_waterheaterSpecs['house']]
            df_waterheaterSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_waterheaterSpecs['house']]
            df_waterheaterSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_waterheaterSpecs['house']]
            df_waterheaterSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_waterheaterSpecs['house']]
            
            ### other specs
            for i in range(10):
                df_waterheaterSpecs['s{}'.format(i)] = 0
                df_waterheaterSpecs['e{}'.format(i)] = 24
                # NOTE s0..s9 are starting hours, e0..e9 are ending hours
            
            df_waterheaterSpecs['connected'] = 1
            df_waterheaterSpecs['load_class'] ='tcl'
            df_waterheaterSpecs['load_type'] ='waterheater'
            
            df_waterheaterSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_waterheaters)
            df_waterheaterSpecs['skew'] = 0
            df_waterheaterSpecs['irradiance'] = 0
            df_waterheaterSpecs['irradiance_roof'] = 0
            df_waterheaterSpecs['irradiance_wall1'] = 0
            df_waterheaterSpecs['irradiance_wall2'] = 0
            df_waterheaterSpecs['irradiance_wall3'] = 0
            df_waterheaterSpecs['irradiance_wall4'] = 0
            
            df_waterheaterSpecs['counter'] = np.random.uniform(0, 10, n_waterheaters)
            df_waterheaterSpecs['min_cycletime'] = np.random.uniform(3, 5, n_waterheaters) 
            df_waterheaterSpecs['min_coolingtime'] = np.random.uniform(2, 5, n_waterheaters)
            df_waterheaterSpecs['min_heatingtime'] = np.random.uniform(2, 5, n_waterheaters)
            
            df_waterheaterSpecs['min_chargingtime'] = 5
            df_waterheaterSpecs['min_dischargingtime'] = 5
            df_waterheaterSpecs['charging_counter'] = 5
            df_waterheaterSpecs['discharging_counter'] = 5
            
            #---initial conditions
            ### save specs
            df_waterheaterSpecs.to_csv('./specs/waterheaterSpecs.csv', index=False, mode='w')
            print("Created ./specs/waterheaterSpecs.csv, {} units.".format(n_waterheaters))
            df_houseSpecs.reset_index(drop=True, inplace=True)
    if report: print(df_waterheaterSpecs.head(10))
    return df_waterheaterSpecs


# ## --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_waterheaterSpecs(n_waterheaters=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
# ## end test



def create_nntclSpecs(n_nntcls, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for Non-urgent Non-Thermostatically Controlled Loads
    Input:
        n_nntcls = number of NNTCLs
        ldc_adoption = percento of ldc capable devices
        df_houseSpecs = specifications of the houses
        renew = True if new specifications are required
    Output:
        df_nntclSpecs
    '''

    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for NNTCL
    try:
        df_nntclSpecs = pd.read_csv('./specs/nntclSpecs.csv')
        if (len(df_nntclSpecs) < n_nntcls) or renew: raise Exception
    except Exception as e:
        df_nntclSpecs = pd.DataFrame()
        if n_nntcls > 0:
            #---Create distribution of EV capacity
            for i in range(n_nntcls):
                if i < len(df_houseSpecs.index):
                    df_nntclSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_nntclSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            

            # df_nntclSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_nntcls)
            
            # df_nntclSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_nntclSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_nntclSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_nntclSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_nntclSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_nntclSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_nntcls)
            df_nntclSpecs['name'] = ['NN' + "%03d" % i for i in range(1, 1+n_nntcls)]
            df_nntclSpecs['duration'] = FUNCTIONS.populate(n_nntcls, 0.1, 2., 1.0) # [h] total hours of uninterrupted operation
            df_nntclSpecs['power'] = FUNCTIONS.populate(n_nntcls, 0.1, 1.5, 0.3) # [kW] power demand
            df_nntclSpecs['efficiency'] = FUNCTIONS.populate(n_nntcls, 0.9, 0.98, 0.95) # [0..1] efficiency
            df_nntclSpecs['progress'] = np.zeros(n_nntcls) # [0..1]current job status
            # df_nntclSpecs['job_start'] = FUNCTIONS.populate(n_nntcls, 16.5, 21.0, 19.5) # [hourOfTheDay] earliest time to start job
            # df_nntclSpecs['job_finish'] = FUNCTIONS.populate(n_nntcls, 5.0, 6.0, 5.0) # [hourOfTheDay] latest time to finish job

            df_nntclSpecs['proposed_status'] = 0 #np.random.choice([0, 1],n_nntcls,p=[0.5, 0.5])
            df_nntclSpecs['actual_status'] = 0 #df_nntclSpecs['proposed_status']
            df_nntclSpecs['proposed_demand'] = 0
            df_nntclSpecs['actual_demand'] = 0
            df_nntclSpecs['progress'] = 0 #np.multiply(df_nntclSpecs['actual_status'], df_nntclSpecs['progress'])
            df_nntclSpecs['mode'] = 0

            df_nntclSpecs['priority'] = np.random.uniform(20,80,n_nntcls)
            

            df_nntclSpecs['with_dr'] = np.random.choice([True, False], n_nntcls, p=[ldc_adoption, 1-ldc_adoption])
            df_nntclSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_nntclSpecs['house']]
            df_nntclSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_nntclSpecs['house']]
            df_nntclSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_nntclSpecs['house']]
            df_nntclSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_nntclSpecs['house']]
            # multicasting ip and ports
            df_nntclSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_nntclSpecs['house']]
            df_nntclSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_nntclSpecs['house']]
            df_nntclSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_nntclSpecs['house']]
            df_nntclSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_nntclSpecs['house']]
            
            ### save specs
            # df_nntclSpecs.to_csv('./specs/nntclSpecs.csv', index=False, mode='w')
            # df_houseSpecs.reset_index(drop=True, inplace=True)
            # print("Created nntclSpecs.csv, {} units.".format(n_nntcls))

            print("Created nntclSpecs, {} units.".format(n_nntcls))
    if report: print(df_nntclSpecs.head(10))
    return df_nntclSpecs




def create_clotheswasherSpecs(n_clotheswashers, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for clotheswasher
    Input:
        n_clotheswashers = number of units
        ldc_adoption = percento of ldc capable devices
        df_houseSpecs = specifications of the houses
        renew = True if new specifications are required
    Output:
        df_clotheswasherSpecs
    '''

    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for NNTCL
    try:
        df_clotheswasherSpecs = pd.read_csv('./specs/clotheswasherSpecs.csv')
        if (len(df_clotheswasherSpecs) < n_clotheswashers) or renew: raise Exception
    except Exception as e:
        df_clotheswasherSpecs = pd.DataFrame()
        if n_clotheswashers > 0:
            #---Create distribution of EV capacity
            for i in range(n_clotheswashers):
                if i < len(df_houseSpecs.index):
                    df_clotheswasherSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_clotheswasherSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            

            # df_clotheswasherSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_clotheswashers)
            
            # df_clotheswasherSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_clotheswasherSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_clotheswasherSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_clotheswasherSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_clotheswasherSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_clotheswasherSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_clotheswashers)
            df_clotheswasherSpecs['name'] = ['CW' + "%03d" % i for i in range(1, 1+n_clotheswashers)]
            df_clotheswasherSpecs['duration'] = FUNCTIONS.populate(n_clotheswashers, 0.1, 2., 1.0) # [h] total hours of uninterrupted operation
            df_clotheswasherSpecs['power'] = FUNCTIONS.populate(n_clotheswashers, 0.1, 1.5, 0.3) # [kW] power demand
            df_clotheswasherSpecs['model'] = np.random.choice(list_clotheswasher, size=n_clotheswashers)
            df_clotheswasherSpecs['efficiency'] = FUNCTIONS.populate(n_clotheswashers, 0.9, 0.98, 0.95) # [0..1] efficiency
            df_clotheswasherSpecs['progress'] = np.zeros(n_clotheswashers) # [0..1]current job status
            # df_clotheswasherSpecs['job_start'] = FUNCTIONS.populate(n_clotheswashers, 16.5, 21.0, 19.5) # [hourOfTheDay] earliest time to start job
            # df_clotheswasherSpecs['job_finish'] = FUNCTIONS.populate(n_clotheswashers, 5.0, 6.0, 5.0) # [hourOfTheDay] latest time to finish job

            df_clotheswasherSpecs['proposed_status'] = 0 #np.random.choice([0, 1],n_clotheswashers,p=[0.5, 0.5])
            df_clotheswasherSpecs['actual_status'] = 0 #df_clotheswasherSpecs['proposed_status']
            df_clotheswasherSpecs['proposed_demand'] = 0
            df_clotheswasherSpecs['actual_demand'] = 0
            df_clotheswasherSpecs['progress'] = 0 # np.multiply(df_clotheswasherSpecs['actual_status'], df_clotheswasherSpecs['progress'])

            df_clotheswasherSpecs['mode'] = 0
            df_clotheswasherSpecs['priority'] = np.random.uniform(20,80,n_clotheswashers)
            

            df_clotheswasherSpecs['with_dr'] = np.random.choice([True, False], n_clotheswashers, p=[ldc_adoption, 1-ldc_adoption])
            df_clotheswasherSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_clotheswasherSpecs['house']]
            df_clotheswasherSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_clotheswasherSpecs['house']]
            df_clotheswasherSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_clotheswasherSpecs['house']]
            df_clotheswasherSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_clotheswasherSpecs['house']]
            # multicasting ip and ports
            df_clotheswasherSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_clotheswasherSpecs['house']]
            df_clotheswasherSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_clotheswasherSpecs['house']]
            df_clotheswasherSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_clotheswasherSpecs['house']]
            df_clotheswasherSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_clotheswasherSpecs['house']]
            
            ### other specs
            ar_s = np.array([np.clip(np.random.normal(16, 1, 10), a_min=0, a_max=24) for i in range(n_clotheswashers)])
            ar_e = np.array([np.clip(np.random.normal(20, 1, 10), a_min=0, a_max=24) for i in range(n_clotheswashers)])

            for i in range(10):
                df_clotheswasherSpecs['s{}'.format(i)] = 0
                df_clotheswasherSpecs['e{}'.format(i)] = 24

            for i in range(n_clotheswashers):
                for j in range(10):
                    df_clotheswasherSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                    df_clotheswasherSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours

            df_clotheswasherSpecs['load_class'] ='ntcl'
            df_clotheswasherSpecs['load_type'] ='clotheswasher'
            
            df_clotheswasherSpecs['profile'] = df_clotheswasherSpecs['model']
            
            df_clotheswasherSpecs['len_profile'] = [len(dict_clotheswasher[x]) for x in df_clotheswasherSpecs['profile'].values]
            df_clotheswasherSpecs['skew'] = 0
            df_clotheswasherSpecs['schedule'] = df_houseSpecs['schedule'].values
            df_clotheswasherSpecs['schedule_skew'] = np.random.randint(-900, 900, n_clotheswashers)
            
            df_clotheswasherSpecs['irradiance'] = 0
            df_clotheswasherSpecs['irradiance_roof'] = 0
            df_clotheswasherSpecs['irradiance_wall1'] = 0
            df_clotheswasherSpecs['irradiance_wall2'] = 0
            df_clotheswasherSpecs['irradiance_wall3'] = 0
            df_clotheswasherSpecs['irradiance_wall4'] = 0
            
            df_clotheswasherSpecs['counter'] = np.random.uniform(0,60, n_clotheswashers)
            df_clotheswasherSpecs['min_cycletime'] = df_clotheswasherSpecs['len_profile'] #np.random.randint(1,3, n_clotheswashers)
            df_clotheswasherSpecs['min_coolingtime'] = np.random.uniform(30, 60, n_clotheswashers)
            df_clotheswasherSpecs['min_heatingtime'] = np.random.uniform(30, 60, n_clotheswashers)
            
            df_clotheswasherSpecs['min_chargingtime'] = 5
            df_clotheswasherSpecs['min_dischargingtime'] = 5
            df_clotheswasherSpecs['charging_counter'] = 5
            df_clotheswasherSpecs['discharging_counter'] = 5
            
            ### save specs
            df_clotheswasherSpecs.to_csv('./specs/clotheswasherSpecs.csv', index=False, mode='w')
            df_houseSpecs.reset_index(drop=True, inplace=True)
            print("Created ./specs/clotheswasherSpecs.csv, {} units.".format(n_clotheswashers))

    if report: print(df_clotheswasherSpecs.head(10))
    return df_clotheswasherSpecs




def create_clothesdryerSpecs(n_clothesdryers, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for clothesdryer
    Input:
        n_clothesdryers = number of units
        ldc_adoption = percento of ldc capable devices
        df_houseSpecs = specifications of the houses
        renew = True if new specifications are required
    Output:
        df_clothesdryerSpecs
    '''

    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for NNTCL
    try:
        df_clothesdryerSpecs = pd.read_csv('./specs/clothesdryerSpecs.csv')
        if (len(df_clothesdryerSpecs) < n_clothesdryers) or renew: raise Exception
    except Exception as e:
        df_clothesdryerSpecs = pd.DataFrame()
        if n_clothesdryers > 0:
            #---Create distribution of EV capacity
            for i in range(n_clothesdryers):
                if i < len(df_houseSpecs.index):
                    df_clothesdryerSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_clothesdryerSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            

            # df_clothesdryerSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_clothesdryers)
            
            # df_clothesdryerSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_clothesdryerSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_clothesdryerSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_clothesdryerSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_clothesdryerSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_clothesdryerSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_clothesdryers)
            df_clothesdryerSpecs['name'] = ['CD' + "%03d" % i for i in range(1, 1+n_clothesdryers)]
            df_clothesdryerSpecs['duration'] = FUNCTIONS.populate(n_clothesdryers, 0.1, 2., 1.0) # [h] total hours of uninterrupted operation
            df_clothesdryerSpecs['power'] = FUNCTIONS.populate(n_clothesdryers, 0.1, 1.5, 0.3) # [kW] power demand
            df_clothesdryerSpecs['model'] = np.random.choice(list_clothesdryer, size=n_clothesdryers)
            df_clothesdryerSpecs['efficiency'] = FUNCTIONS.populate(n_clothesdryers, 0.9, 0.98, 0.95) # [0..1] efficiency
            df_clothesdryerSpecs['progress'] = np.zeros(n_clothesdryers) # [0..1]current job status
            # df_clothesdryerSpecs['job_start'] = FUNCTIONS.populate(n_clothesdryers, 16.5, 21.0, 19.5) # [hourOfTheDay] earliest time to start job
            # df_clothesdryerSpecs['job_finish'] = FUNCTIONS.populate(n_clothesdryers, 5.0, 6.0, 5.0) # [hourOfTheDay] latest time to finish job

            df_clothesdryerSpecs['proposed_status'] = 0 #np.random.choice([0, 1],n_clothesdryers,p=[0.5, 0.5])
            df_clothesdryerSpecs['actual_status'] = 0
            df_clothesdryerSpecs['proposed_demand'] = 0
            df_clothesdryerSpecs['actual_demand'] = 0
            df_clothesdryerSpecs['progress'] = 0

            df_clothesdryerSpecs['mode'] = 0
            df_clothesdryerSpecs['priority'] = np.random.uniform(20,80,n_clothesdryers)
            

            df_clothesdryerSpecs['with_dr'] = np.random.choice([True, False], n_clothesdryers, p=[ldc_adoption, 1-ldc_adoption])
            df_clothesdryerSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_clothesdryerSpecs['house']]
            df_clothesdryerSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_clothesdryerSpecs['house']]
            df_clothesdryerSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_clothesdryerSpecs['house']]
            df_clothesdryerSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_clothesdryerSpecs['house']]
            # multicasting ip and ports
            df_clothesdryerSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_clothesdryerSpecs['house']]
            df_clothesdryerSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_clothesdryerSpecs['house']]
            df_clothesdryerSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_clothesdryerSpecs['house']]
            df_clothesdryerSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_clothesdryerSpecs['house']]
            
            ### other specs
            ar_s = np.array([np.clip(np.random.normal(16, 1, 10), a_min=0, a_max=24) for i in range(n_clothesdryers)])
            ar_e = np.array([np.clip(np.random.normal(23, 1, 10), a_min=0, a_max=24) for i in range(n_clothesdryers)])

            for i in range(10):
                df_clothesdryerSpecs['s{}'.format(i)] = 0
                df_clothesdryerSpecs['e{}'.format(i)] = 24

            for i in range(n_clothesdryers):
                for j in range(10):
                    df_clothesdryerSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                    df_clothesdryerSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours
                    
            df_clothesdryerSpecs['load_class'] ='ntcl'
            df_clothesdryerSpecs['load_type'] ='clothesdryer'
            
            df_clothesdryerSpecs['profile'] = df_clothesdryerSpecs['model']
            df_clothesdryerSpecs['skew'] = 0
            df_clothesdryerSpecs['schedule'] = df_houseSpecs['schedule'].values
            df_clothesdryerSpecs['schedule_skew'] = np.random.randint(-900,900,n_clothesdryers)
            
            df_clothesdryerSpecs['irradiance'] = 0
            df_clothesdryerSpecs['irradiance_roof'] = 0
            df_clothesdryerSpecs['irradiance_wall1'] = 0
            df_clothesdryerSpecs['irradiance_wall2'] = 0
            df_clothesdryerSpecs['irradiance_wall3'] = 0
            df_clothesdryerSpecs['irradiance_wall4'] = 0
            df_clothesdryerSpecs['len_profile'] = [len(dict_clothesdryer[x]) for x in df_clothesdryerSpecs['profile'].values]
            df_clothesdryerSpecs['counter'] = np.random.uniform(0, 60, n_clothesdryers)
            df_clothesdryerSpecs['min_cycletime'] = df_clothesdryerSpecs['len_profile']
            df_clothesdryerSpecs['min_coolingtime'] = np.random.uniform(30, 60, n_clothesdryers)
            df_clothesdryerSpecs['min_heatingtime'] = np.random.uniform(30, 60, n_clothesdryers)
            
            df_clothesdryerSpecs['min_chargingtime'] = 5
            df_clothesdryerSpecs['min_dischargingtime'] = 5
            df_clothesdryerSpecs['charging_counter'] = 5
            df_clothesdryerSpecs['discharging_counter'] = 5
            
            ### save specs
            df_clothesdryerSpecs.to_csv('./specs/clothesdryerSpecs.csv', index=False, mode='w')
            df_houseSpecs.reset_index(drop=True, inplace=True)
            print("Created ./specs/clothesdryerSpecs.csv, {} units.".format(n_clothesdryers))

    if report: print(df_clothesdryerSpecs.head(10))
    return df_clothesdryerSpecs


# def create_clothesdryerSpecs(n_clothesdryers, ldc_adoption, df_houseSpecs, renew=False, report=False):
#     ''' Create specs for Heating Ventilation and Air Conditioning (HVAC)
#     Input:
#         n_clothesdyers = number of clothesdryers
#         ldc_adoption = percent of clothesdryers with ldc capability
#         df_houseSpecs = specs of the houses with clothesdryers
#         renew = True if new specs are required
#     Output:
#         df_clothesdryerSpecs = dataframe containing clothesdryer specs

#     '''
#     #---house indices and probabilities
#     probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs['floor_area']))

#     #---create specs for clothesdryers
#     try:
#         df_clothesdryerSpecs =  pd.read_csv('./specs/clothesdryerSpecs.csv', header=0)
        
#         if (len(df_clothesdryerSpecs)< n_clothesdryers) or renew: raise Exception
#     except Exception as e:
#         df_clothesdryerSpecs = pd.DataFrame()
#         if n_clothesdryers > 0:
#             try:
#                 #---property distribution of clothesdryers ---
#                 df_clothesdryerSpecs['house'] = df_houseSpecs['name'].values

#                 # df_clothesdryerSpecs.loc[range(5,len(df_houseSpecs.index)),'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], size=n_clothesdryers, replace=False)
#                 # df_clothesdryerSpecs.loc[0, 'house'] = df_houseSpecs.loc[0, 'name']
#                 # df_clothesdryerSpecs.loc[1, 'house'] = df_houseSpecs.loc[1, 'name']
#                 # df_clothesdryerSpecs.loc[2, 'house'] = df_houseSpecs.loc[2, 'name']
#                 # df_clothesdryerSpecs.loc[3, 'house'] = df_houseSpecs.loc[3, 'name']
#                 # df_clothesdryerSpecs.loc[4, 'house'] = df_houseSpecs.loc[4, 'name']

#                 df_houseSpecs.index = df_houseSpecs['name'].values
#                 df_clothesdryerSpecs['name'] = ['AC' + "%03d" % i for i in range(1, 1+n_clothesdryers)]
#                 df_clothesdryerSpecs['with_dr'] = np.random.choice([True, False], n_clothesdryers, p=[ldc_adoption, 1-ldc_adoption])
#                 df_clothesdryerSpecs['cop'] = 1  # cop = HEAT/Work
#                 #---temperature setpoints--- NOTE: heating_setpoint < cooling setpoint
#                 df_clothesdryerSpecs['heating_setpoint'] = FUNCTIONS.populate(n_clothesdryers, 21.0, 23.0, 22.)  
#                 df_clothesdryerSpecs['cooling_setpoint'] = df_clothesdryerSpecs['heating_setpoint']
#                 df_clothesdryerSpecs['tolerance'] = np.random.choice(np.arange(0.1, 0.5, 0.1), replace=True, size=n_clothesdryers)  # [degC] deadband (+ or -)
#                 df_clothesdryerSpecs['temp_max'] = np.add(df_clothesdryerSpecs['heating_setpoint'].values, 0.5) #np.random.choice(np.arange(25.0, 26.0, 0.1), replace=True, size=n_clothesdryers) # [degC]
#                 df_clothesdryerSpecs['temp_min'] = np.subtract(df_clothesdryerSpecs['heating_setpoint'].values, 3) #np.random.choice(np.arange(19.0, 20.0, 0.1), replace=True, size=n_clothesdryers) # [degC]

#                 df_clothesdryerSpecs['temp_in'] = np.add(df_clothesdryerSpecs['heating_setpoint'].values, np.random.normal(0, 1, n_clothesdryers))
#                 df_clothesdryerSpecs['temp_mat'] = np.add(df_clothesdryerSpecs['heating_setpoint'].values, np.random.normal(0, 1, n_clothesdryers))
                
#                 df_clothesdryerSpecs['temp_out'] = np.clip(np.random.normal(22, 0.5, n_clothesdryers), a_min=10, a_max=26) # [degC]
#                 df_clothesdryerSpecs['proposed_status'] = np.random.choice([0, 1],n_clothesdryers,p=[0.5, 0.5])
#                 df_clothesdryerSpecs['actual_status'] = np.random.choice([0, 1],n_clothesdryers,p=[0.5, 0.5])
#                 df_clothesdryerSpecs['mode'] = np.random.choice([0, 1],n_clothesdryers,p=[0.5, 0.5])
#                 df_clothesdryerSpecs['d_priority'] = np.random.choice(np.arange(2, 9, 0.01),n_clothesdryers)
#                 df_clothesdryerSpecs['priority'] = np.random.choice(np.arange(2, 9, 0.01),n_clothesdryers)

#                 #---TCL properties ---      
#                 floor_factor = np.clip(np.random.normal(0.5,0.01, n_houses), a_min=0.4, a_max=1.0)

#                 df_clothesdryerSpecs['floor_area'] = np.multiply(df_houseSpecs['floor_area'].values, floor_factor)
#                 df_clothesdryerSpecs.loc[0, 'floor_area'] = 67.99
#                 df_clothesdryerSpecs.loc[1, 'floor_area'] = 11.69
#                 df_clothesdryerSpecs.loc[2, 'floor_area'] = 14.00
#                 df_clothesdryerSpecs.loc[3, 'floor_area'] = 11.37
#                 df_clothesdryerSpecs.loc[4, 'floor_area'] = 19.87
#                 df_clothesdryerSpecs['ceiling_height'] = df_houseSpecs['ceiling_height'].values
#                 df_clothesdryerSpecs['heating_power_thermal'] = np.round(df_clothesdryerSpecs['floor_area'].values * 80, -2)
#                 df_clothesdryerSpecs['heating_power'] = df_clothesdryerSpecs['heating_power_thermal'].values
#                 df_clothesdryerSpecs['cooling_power_thermal'] = 0
#                 df_clothesdryerSpecs['cooling_power'] = 0
#                 df_clothesdryerSpecs['ventilation_power'] = 0
#                 df_clothesdryerSpecs['standby_power'] = FUNCTIONS.populate(n_clothesdryers, 0.95, 1.05, 1 ) * 1.8  #[watts]
                
#                 df_clothesdryerSpecs['min_heatingtime'] = np.random.randint(120, 180, n_clothesdryers) #np.random.choice(np.arange(2.0, 3.0, 0.1), replace=True, size=n_clothesdryers) * 60  # [seconds]
#                 df_clothesdryerSpecs['min_coolingtime'] = 0
#                 df_clothesdryerSpecs['cooling_counter'] = 0
#                 df_clothesdryerSpecs['heating_counter'] = np.random.randint(0, 120, n_clothesdryers)
#                 df_clothesdryerSpecs['charging_counter'] = np.random.randint(0, 120, n_clothesdryers)
#                 df_clothesdryerSpecs['discharging_counter'] = np.random.randint(0, 120, n_clothesdryers)
                
#                 df_clothesdryerSpecs['mass_change'] = df_houseSpecs[['mass_change']].values
#                 df_clothesdryerSpecs['volume'] = [ch * fa for ch, fa in zip(df_houseSpecs['ceiling_height'].values, df_clothesdryerSpecs['floor_area'].values)] # [m^3]

#                 df_clothesdryerSpecs['Ua'] = [(x1/y1) + (x2/y2) + (x3/y3) + (x4/y4) + (x5/y5) for x1,y1,x2,y2,x3,y3,x4,y4,x5,y5 in zip(df_houseSpecs['roof_area'], df_houseSpecs['R_roof'],
#                     df_houseSpecs['wall_area'], df_houseSpecs['R_wall'], 
#                     df_houseSpecs['floor_area'], df_houseSpecs['R_floor'], 
#                     df_houseSpecs['window_area'], df_houseSpecs['R_window'], 
#                     df_houseSpecs['skylight_area'], df_houseSpecs['R_skylight'])]

#                 df_clothesdryerSpecs['Ua'] = np.multiply(df_clothesdryerSpecs['Ua'].values, np.divide(df_clothesdryerSpecs['floor_area'].values, df_houseSpecs['floor_area'].values)) * 0.7 # 0.7 factor to decrease Um since at most only two walls are exposed outside
#                 df_clothesdryerSpecs['Um'] = df_clothesdryerSpecs['volume'] * 1 * 66.67  # [W/degC]
#                 df_clothesdryerSpecs['Ca'] = df_clothesdryerSpecs['volume'] * 0.8 * 1006.0 * np.mean(df_houseSpecs['air_density'])  # [m^3][J/kg.degC][kg/m^3]
#                 df_clothesdryerSpecs['Cm'] = df_clothesdryerSpecs['volume'] * 0.2 * 4180 * 1000 # [m^3][Vmat/Vair][J/kg.degC][kg/m^3]  water
#                 df_clothesdryerSpecs['Cp'] = 1006.0  # [J/kg.degC]

#                 df_clothesdryerSpecs['mass_fraction_external_heat'] = df_houseSpecs['mass_fraction_external_heat'].values
#                 df_clothesdryerSpecs['mass_fraction_internal_heat'] = df_houseSpecs['mass_fraction_internal_heat'].values
#                 df_clothesdryerSpecs['schedule_skew'] = df_houseSpecs['schedule_skew'].values
#                 df_clothesdryerSpecs['phase'] = df_houseSpecs['phase'].values
#                 df_clothesdryerSpecs['voltage'] = df_houseSpecs['voltage'].values
#                 df_clothesdryerSpecs['angle'] = df_houseSpecs['angle'].values
#                 df_clothesdryerSpecs['frequency'] = df_houseSpecs['frequency'].values      
#                 # multicasting ip and ports
#                 df_clothesdryerSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_clothesdryerSpecs['house']]
#                 df_clothesdryerSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_clothesdryerSpecs['house']]
#                 df_clothesdryerSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_clothesdryerSpecs['house']]
#                 df_clothesdryerSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_clothesdryerSpecs['house']]

#                 ### add running schedules
#                 dict_sched = {'morning':[7,9], 'day':[9,17], 'evening':[17,23], 'night':[23,7], '24h':[0,24]}
#                 s = [np.random.choice(['morning', 'day', 'evening', 'night', '24h'], p=[0.30, 0.18, 0.32, 0.11, 0.09], size=10) for i in range(n_clothesdryers)]  #p=[0.30, 0.18, 0.32, 0.11, 0.09]
#                 ar_s = []
#                 ar_e = []
#                 for i in s:
#                     ar_s.append([dict_sched[i[j]][0] for j in range(10)])
#                     ar_e.append([dict_sched[i[j]][1] for j in range(10)])
                
#                 ar_s = np.array(ar_s)
#                 ar_e = np.array(ar_e)

#                 for i in range(10):
#                     df_clothesdryerSpecs['s{}'.format(i)] = 0
#                     df_clothesdryerSpecs['e{}'.format(i)] = 24
                
#                 # for i in range(n_clothesdryers):
#                 #     for j in range(10):
#                 #         df_clothesdryerSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
#                 #         df_clothesdryerSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]

#                 ### other specs
#                 df_clothesdryerSpecs['load_class'] = 'tcl'
#                 df_clothesdryerSpecs['load_type']= 'clothesdryer'
#                 df_clothesdryerSpecs['d_priority'] = np.random.randint(0,100)
                
#                 df_clothesdryerSpecs['profile'] = np.random.choice(list(df_baseload), replace=True, size=n_clothesdryers)
#                 df_clothesdryerSpecs['skew'] = 0
#                 df_clothesdryerSpecs['irradiance'] = 0
#                 df_clothesdryerSpecs['irradiance_roof'] = 0
#                 df_clothesdryerSpecs['irradiance_wall1'] = 0
#                 df_clothesdryerSpecs['irradiance_wall2'] = 0
#                 df_clothesdryerSpecs['irradiance_wall3'] = 0
#                 df_clothesdryerSpecs['irradiance_wall4'] = 0
                
#                 df_clothesdryerSpecs['min_cycletime']= np.random.randint(1,3, n_clothesdryers) * 0
#                 df_clothesdryerSpecs['min_coolingtime']= np.random.randint(1,3, n_clothesdryers) * 0
#                 df_clothesdryerSpecs['min_heatingtime']= np.random.randint(1,3, n_clothesdryers) * 0
                
#                 df_clothesdryerSpecs['min_chargingtime'] = 5
#                 df_clothesdryerSpecs['min_dischargingtime'] = 5
#                 df_clothesdryerSpecs['charging_counter'] = 5
#                 df_clothesdryerSpecs['discharging_counter'] = 5

#                 ### save specs
#                 df_clothesdryerSpecs.to_csv('./specs/clothesdryerSpecs.csv', index=False, mode='w')
#                 print("Created ./specs/clothesdryerSpecs.csv, {} units.".format(n_clothesdryers))
#                 df_houseSpecs.reset_index(drop=True, inplace=True)
#             except Exception as e:
#                 print("error create clothesdryerSpecs:",e)
#     if report: print(df_clothesdryerSpecs.head(10))
#     return df_clothesdryerSpecs




def create_dishwasherSpecs(n_dishwashers, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for dishwasher
    Input:
        n_dishwashers = number of units
        ldc_adoption = percento of ldc capable devices
        df_houseSpecs = specifications of the houses
        renew = True if new specifications are required
    Output:
        df_dishwasherSpecs
    '''

    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for NNTCL
    try:
        df_dishwasherSpecs = pd.read_csv('./specs/dishwasherSpecs.csv')
        if (len(df_dishwasherSpecs) < n_dishwashers) or renew: raise Exception
    except Exception as e:
        df_dishwasherSpecs = pd.DataFrame()
        if n_dishwashers > 0:
            #---Create distribution of EV capacity
            for i in range(n_dishwashers):
                if i < len(df_houseSpecs.index):
                    df_dishwasherSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_dishwasherSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            

            # df_dishwasherSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_dishwashers)
            
            # df_dishwasherSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_dishwasherSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_dishwasherSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_dishwasherSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_dishwasherSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_dishwasherSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_dishwashers)
            df_dishwasherSpecs['name'] = ['DW' + "%03d" % i for i in range(1, 1+n_dishwashers)]
            df_dishwasherSpecs['duration'] = FUNCTIONS.populate(n_dishwashers, 0.1, 2., 1.0) # [h] total hours of uninterrupted operation
            df_dishwasherSpecs['power'] = FUNCTIONS.populate(n_dishwashers, 0.1, 1.5, 0.3) # [kW] power demand
            df_dishwasherSpecs['model'] = np.random.choice(list_dishwasher, size=n_dishwashers)
            df_dishwasherSpecs['efficiency'] = FUNCTIONS.populate(n_dishwashers, 0.9, 0.98, 0.95) # [0..1] efficiency
            df_dishwasherSpecs['progress'] = np.zeros(n_dishwashers) # [0..1]current job status
            # df_dishwasherSpecs['job_start'] = FUNCTIONS.populate(n_dishwashers, 16.5, 21.0, 19.5) # [hourOfTheDay] earliest time to start job
            # df_dishwasherSpecs['job_finish'] = FUNCTIONS.populate(n_dishwashers, 5.0, 6.0, 5.0) # [hourOfTheDay] latest time to finish job

            df_dishwasherSpecs['proposed_status'] = 0 #np.random.choice([0, 1],n_dishwashers,p=[0.5, 0.5])
            df_dishwasherSpecs['actual_status'] = 0 #df_dishwasherSpecs['proposed_status']
            df_dishwasherSpecs['proposed_demand'] = 0
            df_dishwasherSpecs['actual_demand'] = 0
            df_dishwasherSpecs['progress'] = 0 #np.multiply(df_dishwasherSpecs['progress'], df_dishwasherSpecs['actual_status'])

            df_dishwasherSpecs['mode'] = 0
            df_dishwasherSpecs['priority'] = np.random.uniform(20,80,n_dishwashers)
            

            df_dishwasherSpecs['with_dr'] = np.random.choice([True, False], n_dishwashers, p=[ldc_adoption, 1-ldc_adoption])
            df_dishwasherSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_dishwasherSpecs['house']]
            df_dishwasherSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_dishwasherSpecs['house']]
            df_dishwasherSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_dishwasherSpecs['house']]
            df_dishwasherSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_dishwasherSpecs['house']]
            # multicasting ip and ports
            df_dishwasherSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_dishwasherSpecs['house']]
            df_dishwasherSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_dishwasherSpecs['house']]
            df_dishwasherSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_dishwasherSpecs['house']]
            df_dishwasherSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_dishwasherSpecs['house']]
            
            ### other specs
            ar_s = np.array([np.clip(np.random.normal(17, 1, 10), a_min=0, a_max=24) for i in range(n_dishwashers)])
            ar_e = np.array([np.clip(np.random.normal(5, 1, 10), a_min=0, a_max=24) for i in range(n_dishwashers)])

            for i in range(10):
                df_dishwasherSpecs['s{}'.format(i)] = 0
                df_dishwasherSpecs['e{}'.format(i)] = 24

            for i in range(n_dishwashers):
                for j in range(10):
                    df_dishwasherSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                    df_dishwasherSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours
                    
            df_dishwasherSpecs['load_class'] ='ntcl'
            df_dishwasherSpecs['load_type'] ='dishwasher'
            
            df_dishwasherSpecs['profile'] = df_dishwasherSpecs['model']
            df_dishwasherSpecs['len_profile'] = [len(dict_dishwasher[x]) for x in df_dishwasherSpecs['profile'].values]
            df_dishwasherSpecs['skew'] = 0
            df_dishwasherSpecs['schedule'] = df_houseSpecs['schedule'].values
            df_dishwasherSpecs['schedule_skew'] = np.random.randint(-900, 900, n_dishwashers) #[hours]
            
            df_dishwasherSpecs['irradiance'] = 0
            df_dishwasherSpecs['irradiance_roof'] = 0
            df_dishwasherSpecs['irradiance_wall1'] = 0
            df_dishwasherSpecs['irradiance_wall2'] = 0
            df_dishwasherSpecs['irradiance_wall3'] = 0
            df_dishwasherSpecs['irradiance_wall4'] = 0
            
            df_dishwasherSpecs['counter'] = np.random.uniform(0, 60, n_dishwashers)
            df_dishwasherSpecs['min_cycletime'] = df_dishwasherSpecs['len_profile'] #np.random.randint(1,3, n_dishwashers) * 0
            df_dishwasherSpecs['min_coolingtime'] = np.random.uniform(30, 60, n_dishwashers)
            df_dishwasherSpecs['min_heatingtime'] = np.random.uniform(30, 60, n_dishwashers)
            
            df_dishwasherSpecs['min_chargingtime'] = 5
            df_dishwasherSpecs['min_dischargingtime'] = 5
            df_dishwasherSpecs['charging_counter'] = 5
            df_dishwasherSpecs['discharging_counter'] = 5
            
            ### save specs
            df_dishwasherSpecs.to_csv('./specs/dishwasherSpecs.csv', index=False, mode='w')
            df_houseSpecs.reset_index(drop=True, inplace=True)
            print("Created ./specs/dishwasherSpecs.csv, {} units.".format(n_dishwashers))
    if report: print(df_dishwasherSpecs.head(10))
    return df_dishwasherSpecs






# ## --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_nntclSpecs(n_nntcls=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
# ## end test



def create_evSpecs(n_evs, ldc_adoption, v2g_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specification for Electric Vehicles
    Input:
        n_evs = number of EVs
        ldc_adoption = percent of ldc capable EV chargers
        df_houseSpecs = house specs
        renew = True if new specifications are required
    ''' 
    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for EVs
    try:
        df_evSpecs = pd.read_csv('./specs/evSpecs.csv')
        if (len(df_evSpecs) < n_evs) or renew: raise Exception
    except Exception as e:
        df_evSpecs = pd.DataFrame()
        if n_evs > 0:
            #---Create distribution of EV capacity
            for i in range(n_evs):
                if i < len(df_houseSpecs.index):
                    df_evSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_evSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            
            # df_evSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_evs)
            
            # df_evSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_evSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_evSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_evSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_evSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_evSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_evs)
            df_evSpecs['name'] = ['EV' + "%03d" % i for i in range(1, 1+n_evs)]
            df_evSpecs['load_type'] = 'ev'
            df_evSpecs['capacity'] = FUNCTIONS.populate(n_evs, 5.2, 85., 24.) * 1000 * 3600 # [J] or watts.second
            df_evSpecs['charging_power'] = FUNCTIONS.populate(n_evs, 1.8, 7.5, 3.5) * 1000 # [W] charging rate in W at home
            df_evSpecs['charging_efficiency'] = FUNCTIONS.populate(n_evs, 0.85, 0.95, 0.90) # [0..1] charging efficiency
            df_evSpecs['soc'] = np.random.uniform(0.5, 1.0, n_evs) # [0..1]current charge status

            df_evSpecs['min_chargingtime'] = np.random.randint(0, 60, n_evs)
            df_evSpecs['min_dischargingtime'] = df_evSpecs['min_chargingtime'].values
            df_evSpecs['cooling_counter'] = np.random.randint(0, 60, n_evs)  # neglected 
            df_evSpecs['heating_counter'] = np.random.randint(0, 60, n_evs)  # neglected
            df_evSpecs['charging_counter'] = np.random.randint(0, 60, n_evs)
            df_evSpecs['discharging_counter'] = np.random.randint(0, 60, n_evs)
            
            df_evSpecs['target_soc'] = FUNCTIONS.populate(n_evs, 0.99, 1.0, 0.99) # [0..1]current charge status
            df_evSpecs['hour_start'] = FUNCTIONS.populate(n_evs, 17., 21., 19.5) # [hourOfTheDay] earliest time to start charging, time when EV arrived and start charging
            df_evSpecs['hour_end'] = FUNCTIONS.populate(n_evs, 6.5, 7., 7.) # [hourOfTheDay] latest time to finish charging, time when EV shall be used
            df_evSpecs['leakage'] = FUNCTIONS.populate(n_evs,0.9*1e-7, 1.1*1e-7, 1e-7) #[0..1] charge loss at standby mode
            df_evSpecs['trip_distance'] = FUNCTIONS.populate(n_evs, 10, 50, 20) # [km] avg daily trip
            df_evSpecs['trip_time'] = FUNCTIONS.populate(n_evs, 0.25, 2, 0.75) #[hours] avg daily trip
            df_evSpecs['km_per_kwh'] = FUNCTIONS.populate(n_evs, 4.225, 6.76, 6.5) #[km/kWh] 1kWh per 6.5 km avg 
            df_evSpecs['with_dr'] = np.random.choice([True, False], n_evs, p=[ldc_adoption, 1-ldc_adoption])
            df_evSpecs['with_v2g'] = np.random.choice([True, False], n_evs, p=[v2g_adoption, 1-v2g_adoption])
            
            df_evSpecs['proposed_status'] = np.random.choice([0, 1],n_evs,p=[0.9, 0.1])
            df_evSpecs['actual_status'] = np.random.choice([0, 1],n_evs,p=[0.9, 0.1])
            df_evSpecs['proposed_demand'] = 0
            df_evSpecs['actual_demand'] = 0
            df_evSpecs['mode'] = np.random.choice([0, 1],n_evs,p=[0.5, 0.5])
            df_evSpecs['priority'] = np.random.uniform(20,80,n_evs)
            

            df_evSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_evSpecs['house']]
            df_evSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_evSpecs['house']]
            df_evSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_evSpecs['house']]
            df_evSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_evSpecs['house']]
            # multicasting ip and ports
            df_evSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_evSpecs['house']]
            df_evSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_evSpecs['house']]
            df_evSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_evSpecs['house']]
            df_evSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_evSpecs['house']]
            
            ### other specs
            ar_s = np.array([np.clip(np.random.normal(18, 0.5, 10), a_min=0, a_max=24) for i in range(n_evs)])
            ar_e = np.array([np.clip(np.random.normal(6, 1, 10), a_min=0, a_max=24) for i in range(n_evs)])

            for i in range(10):
                df_evSpecs['s{}'.format(i)] = 0
                df_evSpecs['e{}'.format(i)] = 24

            for i in range(n_evs):
                for j in range(10):
                    df_evSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                    df_evSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours
                    
            df_evSpecs['load_class'] ='battery'
            df_evSpecs['load_type'] ='ev'
            
            df_evSpecs['profile'] = np.random.choice(['tesla_s85_90kwh',
                'tesla_s60_60kwh','tesla_3_75kwh', 'nissan_leaf_30kwh', 
                'ford_focus_23kwh','ford_focus_33kwh',
                'mitsubishi_imiev_16kwh', 'chevy_volt_16kwh', 
                'tesla_powerwall_13kwh'], replace=True, size=n_evs)
            df_evSpecs['skew'] = 0
            df_evSpecs['irradiance'] = 0
            df_evSpecs['irradiance_roof'] = 0
            df_evSpecs['irradiance_wall1'] = 0
            df_evSpecs['irradiance_wall2'] = 0
            df_evSpecs['irradiance_wall3'] = 0
            df_evSpecs['irradiance_wall4'] = 0
            
            df_evSpecs['counter'] = np.random.uniform(0, 60, n_evs)
            df_evSpecs['min_cycletime'] = np.random.uniform(3,60, n_evs)
            df_evSpecs['min_coolingtime'] = np.random.uniform(3,60, n_evs)
            df_evSpecs['min_heatingtime'] = np.random.uniform(3,60, n_evs)
            
            df_evSpecs['min_chargingtime'] = 5
            df_evSpecs['min_dischargingtime'] = 5
            df_evSpecs['charging_counter'] = 5
            df_evSpecs['discharging_counter'] = 5
            
            ### save specs
            df_evSpecs.to_csv('./specs/evSpecs.csv', index=False, mode='w')
            print("Created ./specs/evSpecs.csv, {} units.".format(n_evs))
            df_houseSpecs.reset_index(drop=True, inplace=True)
    if report: print(df_evSpecs.head(10))
    return df_evSpecs

    
## --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_evSpecs(n_evs=20, ldc_adoption=1.0, v2g_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
## end test



def create_storageSpecs(n_storages, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for home battery storages
    Input:
        n_storages = number of homes with battery storage
        ldc_adoption = percent of the devices with ldc capability
        df_houseSpecs = house specs
        renew = True if new battery specs are required
    Output:
        df_storageSpecs
    '''
    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create specs for battery storage
    try:
        df_storageSpecs = pd.read_csv('./specs/storageSpecs.csv')
        if (len(df_storageSpecs) < n_storages) or renew: raise Exception
    except Exception as e:
        df_storageSpecs = pd.DataFrame()
        if n_storages > 0:
            #---Create distribution of battery storage
            for i in range(n_storages):
                if i < len(df_houseSpecs.index):
                    df_storageSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_storageSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            
            # df_storageSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_storages)
            
            # df_storageSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_storageSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_storageSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_storageSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_storageSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            df_storageSpecs['name'] = ['SG' + "%03d" % i for i in range(1, 1+n_storages)]
            # df_storageSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_storages)
            df_storageSpecs['capacity'] = FUNCTIONS.populate(n_storages, 6.4, 13.5, 6.4)  # [kWh] to be converted to watt-hour in object creation
            df_storageSpecs['charging_power'] = FUNCTIONS.populate(n_storages, 5, 7, 5) # [kW] charging rate in kW at home
            df_storageSpecs['charging_efficiency'] = FUNCTIONS.populate(n_storages, 0.85, 0.95, 0.9) # [0..1] charging efficiency
            df_storageSpecs['soc'] = FUNCTIONS.populate(n_storages, 0.35, 1.0, 0.75) # [0..1]current charge status
            df_storageSpecs['target_soc'] = FUNCTIONS.populate(n_storages, 0.85, 0.95, 0.9) # [0..1]current charge status

            df_storageSpecs['min_chargingtime'] = np.random.randint(0, 60, n_storages)
            df_storageSpecs['min_dischargingtime'] = df_storageSpecs['min_chargingtime'].values
            df_storageSpecs['cooling_counter'] = np.random.randint(0, 60, n_storages)  # neglected 
            df_storageSpecs['heating_counter'] = np.random.randint(0, 60, n_storages)  # neglected
            df_storageSpecs['charging_counter'] = np.random.randint(0, 60, n_storages)
            df_storageSpecs['discharging_counter'] = np.random.randint(0, 60, n_storages)
            

            df_storageSpecs['proposed_status'] = np.random.choice([0, 1],n_storages,p=[0.9, 0.1])
            df_storageSpecs['actual_status'] = np.random.choice([0, 1],n_storages,p=[0.9, 0.1])
            df_storageSpecs['proposed_demand'] = 0
            df_storageSpecs['actual_demand'] = 0
            df_storageSpecs['mode'] = np.random.choice([0, 1],n_storages,p=[0.5, 0.5])
            df_storageSpecs['priority'] = np.random.uniform(20, 80, n_storages)
            
            # storage_leakage = FUNCTIONS.populate(n_storages,0.9*1e-7, 1.1*1e-7, 1e-7) #[0..1] charge loss at standby mode
            df_storageSpecs['with_dr'] = np.random.choice([True, False], n_storages, p=[ldc_adoption, 1-ldc_adoption])
            df_storageSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_storageSpecs['house']]
            df_storageSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_storageSpecs['house']]
            df_storageSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_storageSpecs['house']]
            df_storageSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_storageSpecs['house']]
            # multicasting ip and ports
            df_storageSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_storageSpecs['house']]
            df_storageSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_storageSpecs['house']]
            df_storageSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_storageSpecs['house']]
            df_storageSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_storageSpecs['house']]
            
            ### other specs
            ar_s = np.array([np.clip(np.random.normal(9, 1, 10), a_min=0, a_max=24) for i in range(n_storages)])
            ar_e = np.array([np.clip(np.random.normal(17, 1, 10), a_min=0, a_max=24) for i in range(n_storages)])

            for i in range(10):
                df_storageSpecs['s{}'.format(i)] = 0
                df_storageSpecs['e{}'.format(i)] = 24

            for i in range(n_storages):
                for j in range(10):
                    df_storageSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                    df_storageSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours
                    
            df_storageSpecs['load_class'] ='battery'
            df_storageSpecs['load_type'] ='storage'
            
            df_storageSpecs['profile'] = np.random.choice(['Powerwall'], replace=True, size=n_storages)
            df_storageSpecs['skew'] = 0
            df_storageSpecs['irradiance'] = 0
            df_storageSpecs['irradiance_roof'] = 0
            df_storageSpecs['irradiance_wall1'] = 0
            df_storageSpecs['irradiance_wall2'] = 0
            df_storageSpecs['irradiance_wall3'] = 0
            df_storageSpecs['irradiance_wall4'] = 0
            
            df_storageSpecs['counter'] = np.random.uniform(0, 60, n_storages)
            df_storageSpecs['min_cycletime'] = np.random.uniform(3, 60, n_storages)
            df_storageSpecs['min_coolingtime'] = np.random.uniform(3, 60, n_storages)
            df_storageSpecs['min_heatingtime'] = np.random.uniform(3, 60, n_storages)
            
            df_storageSpecs['min_chargingtime'] = 5
            df_storageSpecs['min_dischargingtime'] = 5
            df_storageSpecs['charging_counter'] = 5
            df_storageSpecs['discharging_counter'] = 5
            
            ### save specs
            df_storageSpecs.to_csv('./specs/storageSpecs.csv', index=False, mode='w')
            df_houseSpecs.reset_index(drop=True, inplace=True)
            print("Created ./specs/storageSpecs.csv, {} units.".format(n_storages))

    if report: print(df_storageSpecs.head(10))
    return df_storageSpecs

# ## --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_storageSpecs(n_storages=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
# ## end test




def create_pvSpecs(n_pvs, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for solar PVs
    Input:
        n_pvs = number of houses with PVs
        ldc_adoption = percent  of PV inverters with ldc capability
        df_houseSpecs = house specs
        renew = True if new specifications for PVs are required
    Output:
        df_solarSpecs

    As of September 2018, 20,712 solar power systems have been installed in New Zealand. T
    he average residential solar power system size is 4.81kW and the average commercial solar power system size is 14.3kW.[3]
    The largest solar power system on a school in New Zealand was officially opened in a ceremony in February 2019 at Kaitaia College. 
    Hon. Kelvin Davis, unveiled a plaque to acknowledge the installation of the 368 solar panel project which is spread across the rooftop of multiple buildings on the school campus.[4]
    In January 2014, solar photovoltaic systems have been installed in 50 schools through the Schoolgen program, 
    a program developed by Genesis Energy to educate students about renewable energy, particularly solar energy. 
    Each school has been given a 2 kW capacity PV system, with a total distributed installed capacity of 100 kilowatts-peak (kWp). 
    Since February 2007, a total of 513 megawatt-hours (MWh) of electrical energy have been recorded.[5]
    As of 2018, New Zealand's largest solar power plant is at Yealands Estate winery in Marlborough, with a total capacity of 412kW.[6]
    '''
    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))

    #---create solar PV specs
    try:
        df_solarSpecs = pd.read_csv('./specs/pvSpecs.csv')
        if (len(df_solarSpecs) < n_pvs) or renew: raise Exception
    except Exception as e:
        df_solarSpecs = pd.DataFrame()
        if n_pvs > 0:
            #---Solar PV specs---
            for i in range(n_pvs):
                if i < len(df_houseSpecs.index):
                    df_solarSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_solarSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            
            # df_solarSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_pvs)
            
            # df_solarSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_solarSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_solarSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_solarSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_solarSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_solarSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_pvs)
            df_solarSpecs['name'] = ['PV' + "%03d" % i for i in range(1, 1+n_pvs)]
            df_solarSpecs['pv_roof_area'] = FUNCTIONS.populate(n_pvs, 0.25, 0.5, 0.5)  # roof area occupied by solar PV vary from 25% to 50%, with 50% as average
            df_solarSpecs['roof_area'] = df_houseSpecs['roof_area'].values
            df_solarSpecs['power_per_area'] = FUNCTIONS.populate(n_pvs, 0.9*1000./10., 1.1*1000./10., 1000./10.)  # rule of thumb: 1 kW per 10 m^2
            # df_solarSpecs['capacity'] = np.round(np.multiply(np.multiply(df_solarSpecs['pv_roof_area'].values, df_solarSpecs['roof_area']), df_solarSpecs['power_per_area']), -2)
            df_solarSpecs['capacity'] = np.round(np.random.normal(4810, 1000, n_pvs ), -1)
            df_solarSpecs['capacity'] = np.clip(df_solarSpecs['capacity'].values, a_min = 250, a_max=15000)
            df_solarSpecs.loc[0, 'capacity'] = 270*20
            df_solarSpecs.loc[1, 'capacity'] = 0
            df_solarSpecs.loc[2, 'capacity'] = 0
            df_solarSpecs.loc[3, 'capacity'] = 0
            df_solarSpecs.loc[4, 'capacity'] = 270*20
            
            df_solarSpecs['pv_efficiency'] = np.clip(np.random.normal(0.17, 0.01, n_pvs), a_min=0.15, a_max=0.22)
            df_solarSpecs['inverter_efficiency'] = np.clip(np.random.normal(0.9, 0.01, n_pvs), a_min=0.85, a_max=0.96)
            df_solarSpecs['floor_area'] = [df_houseSpecs.loc[n, 'floor_area'] for n in df_solarSpecs['house']]
            df_solarSpecs['latitude'] = [df_houseSpecs.loc[n, 'latitude'] for n in df_solarSpecs['house']]
            df_solarSpecs['longitude'] = [df_houseSpecs.loc[n, 'longitude'] for n in df_solarSpecs['house']]
            df_solarSpecs['elevation'] = [df_houseSpecs.loc[n, 'elevation'] for n in df_solarSpecs['house']]
            df_solarSpecs['albedo'] = [df_houseSpecs.loc[n, 'albedo'] for n in df_solarSpecs['house']]
            df_solarSpecs['roof_tilt'] = [df_houseSpecs.loc[n, 'roof_tilt'] for n in df_solarSpecs['house']]
            df_solarSpecs['azimuth'] = [df_houseSpecs.loc[n, 'azimuth'] for n in df_solarSpecs['house']]
            df_solarSpecs['with_dr'] = np.random.choice([True, False], n_pvs, p=[ldc_adoption, 1-ldc_adoption])
            df_solarSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_solarSpecs['house']]
            df_solarSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_solarSpecs['house']]
            df_solarSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_solarSpecs['house']]
            df_solarSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_solarSpecs['house']]
            # multicasting ip and ports
            df_solarSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_solarSpecs['house']]
            df_solarSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_solarSpecs['house']]
            df_solarSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_solarSpecs['house']]
            df_solarSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_solarSpecs['house']]
            
            ### other specs
            ar_s = np.array([np.clip(np.random.normal(12, 1, 10), a_min=9, a_max=16) for i in range(n_pvs)])  # start of cloud cover
            cloud_duration = np.array([np.clip(np.random.normal(0.01, 0.005, 10), a_min=0.001, a_max=0.1) for i in range(n_pvs)])
            ar_e = np.add(ar_s, cloud_duration) # end of cloud cover

            for i in range(10):
                df_solarSpecs['s{}'.format(i)] = 0
                df_solarSpecs['e{}'.format(i)] = 24

            for i in range(n_pvs):
                for j in range(10):
                    df_solarSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
                    df_solarSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours
                    
            df_solarSpecs['load_class'] ='der'
            df_solarSpecs['load_type'] ='solar'
            
            df_solarSpecs['profile'] = np.random.choice(['Solarcity'], replace=True, size=n_pvs)
            df_solarSpecs['skew'] = 0
            df_solarSpecs['irradiance'] = 0
            df_solarSpecs['irradiance_roof'] = 0
            df_solarSpecs['irradiance_wall1'] = 0
            df_solarSpecs['irradiance_wall2'] = 0
            df_solarSpecs['irradiance_wall3'] = 0
            df_solarSpecs['irradiance_wall4'] = 0
            
            df_solarSpecs['counter'] = np.random.uniform(0, 60, n_pvs)
            df_solarSpecs['min_cycletime'] = np.random.uniform(3, 60, n_pvs)
            df_solarSpecs['min_coolingtime'] = np.random.uniform(3, 60, n_pvs)
            df_solarSpecs['min_heatingtime'] = np.random.uniform(3, 60, n_pvs)
            
            df_solarSpecs['min_chargingtime'] = 5
            df_solarSpecs['min_dischargingtime'] = 5
            df_solarSpecs['charging_counter'] = 5
            df_solarSpecs['discharging_counter'] = 5


            df_solarSpecs['proposed_status'] = 1
            df_solarSpecs['actual_status'] = 1
            df_solarSpecs['proposed_demand'] = 0
            df_solarSpecs['actual_demand'] = 0
            
            ### save specs
            df_solarSpecs.to_csv('./specs/pvSpecs.csv', index=False, mode='w')
            df_houseSpecs.reset_index(drop=True, inplace=True)
            print("Created ./specs/pvSpecs.csv, {} units.".format(n_pvs))
    if report: print(df_solarSpecs.head(10))
    return df_solarSpecs

# ## --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_pvSpecs(n_pvs=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
# ## end test



def create_windSpecs(n_winds, ldc_adoption, df_houseSpecs, renew=False, report=False):
    ''' Create specifications for micro wind turbines
    Input:
        n_winds = number of houses with wind turbines
        ldc_adoption = percent of the inverters with ldc capability
        df_houseSpecs = house specs
        renew = True if new specs for wind turbines are required
    Output:
        df_windSpecs
    '''

    #---house indices and probabilities
    probability = np.array(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area'] / np.sum(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'floor_area']))
    
    #---create specs for wind turbines
    try:
        df_windSpecs = pd.read_csv('./specs/windSpecs.csv')
        if (len(df_windSpecs) < n_winds) or renew: raise Exception
    except Exception as e:
        df_windSpecs = pd.DataFrame()
        if n_winds > 0:
            #---Wind turbing specs---
            for i in range(n_winds):
                if i < len(df_houseSpecs.index):
                    df_windSpecs.loc[i, 'house'] = df_houseSpecs.loc[i,'name']
                else:
                    df_windSpecs.loc[i, 'house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=1)[0]
            
            # df_windSpecs['house'] = np.random.choice(df_houseSpecs.loc[range(5,len(df_houseSpecs.index)),'name'], p=probability, size=n_winds)
            
            # df_windSpecs.loc[0, 'house'] = df_houseSpecs.loc[0,'name']
            # df_windSpecs.loc[1, 'house'] = df_houseSpecs.loc[1,'name']
            # df_windSpecs.loc[2, 'house'] = df_houseSpecs.loc[2,'name']
            # df_windSpecs.loc[3, 'house'] = df_houseSpecs.loc[3,'name']
            # df_windSpecs.loc[4, 'house'] = df_houseSpecs.loc[4,'name']

            df_houseSpecs.index = df_houseSpecs['name'].values
            # df_windSpecs['house'] = np.random.choice(df_houseSpecs['name'], p=probability, size=n_winds)
            df_windSpecs['name'] = ['WD' + "%03d" % i for i in range(1, 1+n_winds)]
            df_windSpecs['installed_capacity'] = FUNCTIONS.populate(n_winds,400.0,1000.0,750.0) # installed wind ranges from 400W to 1000W, with average of 750W
            df_windSpecs['efficiencyWind'] = FUNCTIONS.populate(n_winds, 0.7, 0.9, 0.9)
            df_windSpecs['with_dr'] = np.random.choice([True, False], n_winds, p=[ldc_adoption, 1-ldc_adoption])
            df_windSpecs['phase'] = [df_houseSpecs.loc[n, 'phase'] for n in df_windSpecs['house']]
            df_windSpecs['voltage'] = [df_houseSpecs.loc[n, 'voltage'] for n in df_windSpecs['house']]
            df_windSpecs['angle'] = [df_houseSpecs.loc[n, 'angle'] for n in df_windSpecs['house']]
            df_windSpecs['frequency'] = [df_houseSpecs.loc[n, 'frequency'] for n in df_windSpecs['house']]
            # multicasting ip and ports
            df_windSpecs['mcast_ip_local'] = [df_houseSpecs.loc[n, 'mcast_ip_local'] for n in df_windSpecs['house']]
            df_windSpecs['mcast_port_local'] = [df_houseSpecs.loc[n, 'mcast_port_local'] for n in df_windSpecs['house']]
            df_windSpecs['mcast_ip_global'] = [df_houseSpecs.loc[n, 'mcast_ip_global'] for n in df_windSpecs['house']]
            df_windSpecs['mcast_port_global'] = [df_houseSpecs.loc[n, 'mcast_port_global'] for n in df_windSpecs['house']]
            
            ### other specs
            # ar_s = np.array([np.clip(np.random.normal(13, 1, 10), a_min=0, a_max=24) for i in range(n_winds)])
            # ar_e = np.array([np.clip(np.random.normal(4, 1, 10), a_min=0, a_max=24) for i in range(n_winds)])

            for i in range(10):
                df_windSpecs['s{}'.format(i)] = 0
                df_windSpecs['e{}'.format(i)] = 24

            # for i in range(n_heaters):
            #     for j in range(10):
            #         df_windSpecs.loc[i, 's{}'.format(j)] = ar_s[i, j]
            #         df_windSpecs.loc[i, 'e{}'.format(j)] = ar_e[i, j]
                    # NOTE s0..s9 are starting hours, e0..e9 are ending hours
                    
            df_windSpecs['load_class'] ='der'
            df_windSpecs['load_type'] ='wind'
            
            df_windSpecs['profile'] = np.random.choice(['Vestas'], replace=True, size=n_winds)
            df_windSpecs['skew'] = 0
            df_windSpecs['irradiance'] = 0
            df_windSpecs['irradiance_roof'] = 0
            df_windSpecs['irradiance_wall1'] = 0
            df_windSpecs['irradiance_wall2'] = 0
            df_windSpecs['irradiance_wall3'] = 0
            df_windSpecs['irradiance_wall4'] = 0
            
            df_windSpecs['counter'] = np.random.uniform(0, 60, n_winds)
            df_windSpecs['min_cycletime'] = np.random.uniform(3, 60, n_winds)
            df_windSpecs['min_coolingtime'] = np.random.uniform(3, 60, n_winds)
            df_windSpecs['min_heatingtime'] = np.random.uniform(3, 60, n_winds)
            
            df_windSpecs['min_chargingtime'] = 5
            df_windSpecs['min_dischargingtime'] = 5
            df_windSpecs['charging_counter'] = 5
            df_windSpecs['discharging_counter'] = 5


            df_windSpecs['proposed_status'] = 1
            df_windSpecs['actual_status'] = 1
            df_windSpecs['proposed_demand'] = 0
            df_windSpecs['actual_demand'] = 0
            
            ### save specs
            df_windSpecs.to_csv('./specs/windSpecs.csv', index=False, mode='w')
            df_houseSpecs.reset_index(drop=True, inplace=True)
            print("Created ./specs/windSpecs.csv, {} units.".format(n_winds))

    if report: print(df_windSpecs.head(10))
    
    return df_windSpecs



def create_schedules(renew=False, report=False):
    '''
    create schedules in using different appliances
    n_person = the number of person or users with schedules
    Different appliances are assigned with an integer value(currently based on the ip.address on actual device).
    The status of the device is defined by the decimal part of the schedule.

    weekminute  | P1 | P2| ... 
    1
    2
    3
    4
    360         13.04572  # watervalve1 ON for 4572 seconds
    361         4.13255  # dishwasher, Connected for 13255 seconds
    .
    .
    .
    '''


    dict_appliance = {
        0:'none',
        1:'none',
        2:'none',
        3:'heater',
        4:'dishwasher',
        5:'clothesdryer',
        6:'clotheswasher',
        7:'storage',
        8:'ev',
        9:'fridge',  # always on
        10:'freezer', # always on
        11:'heatpump',  #
        12:'waterheater', # always on
        13:'watervalve1', # hot water, shower
        14:'watervalve2',  # cold water, shower
        15:'watervalve3',  # dump
        16:'humidifier1',  # 
        17:'humidifier2',
        18:'window1',  # lounge
        19:'window2',  # kitchen
        20:'window3',  # bathroom
        21:'window4',  # room2
        22:'window5',  # room1
        23:'door1',  # lounge
        24:'door2',  # bathroom
        25:'door3',  # room 1
        2601:'blind1',  # lounge_north_partial   26 to 41 are controlled by raspi3 192.168.11.126
        2602:'blind2',  # lounge_north_full
        2603:'blind3',  # lounge_east_partial
        2604:'blind4',  # lounge_east_full
        2605:'blind5',  # kitchen_north_full
        2606:'blind6',  # kitchen_east_full
        2607:'blind7',  # kitchen_south_full
        2608:'blind8',  # room2_south_partial
        2609:'blind9',  # room2_south_full
        2610:'blind10',  # room2_west_partial
        2611:'blind11',  # room2_west_full
        2612:'blind12',  # room1_west_partial
        2613:'blind13',  # room1_west_full
        2614:'blind14',  # room1_north_partial
        2615:'blind15',  # room1_north_full
        2616:'blind16',  # all_full
        27:'human1', # humidifier at lounge area
        28:'human2'  # humidifier at guestroom
    }
        
    df_schedule = pd.DataFrame([])
    # df_schedule['weekminute'] = np.arange(0,7*24*60,1).astype(int)
    df_schedule['P1'] = np.zeros(7*24*60)  
    df_schedule['P2'] = np.zeros(7*24*60)  
    df_schedule['P3'] = np.zeros(7*24*60)  
    df_schedule['P4'] = np.zeros(7*24*60)  
    df_schedule['P5'] = np.zeros(7*24*60)  



    indices = []

    ### dishwasher schedule
    dict_sched_dishwasher = { 
        'DW1_1':[[0, 9, 4], [1, 9, 46], [2, 13, 15], [3, 13, 51], [4, 10, 56], [5, 22, 11], [6, 18, 27]],
        'DW1_0':[[0, 17, 4], [1, 17, 46], [2, 18, 15], [3, 18, 51], [4, 16, 56], [6, 4, 11], [6, 23, 27]],
        'DW2_1':[[0, 8, 40], [1, 9, 47], [2, 10, 15], [3, 9, 7], [4, 7, 58], [5, 8, 22], [6, 8, 50]],
        'DW2_0':[[0, 13, 40], [1, 15, 47], [2, 15, 15], [3, 14, 7], [4, 12, 58], [5, 14, 22], [6, 16, 50]],
        'DW3_1':[[0, 8, 45], [0, 21, 56], [1, 21, 21], [2, 12, 52], [3, 9, 11], [4, 8, 51], [4, 16, 57], [5, 20, 30], [6, 15, 26], [6, 21, 16]],
        'DW3_0':[[0, 13, 45], [1, 4, 56], [2, 4, 21], [2, 17, 52], [3, 15, 11], [4, 16, 51], [4, 22, 57], [6, 4, 30], [6, 23, 26], [6, 23, 56]],
        'DW4_1':[[0, 0, 20], [1, 15, 4], [2, 0, 55], [2, 11, 22], [2, 23, 19], [3, 16, 7], [4, 0, 43], [4, 17, 57], [5, 17, 28], [6, 15, 14]],
        'DW4_0':[[0, 5, 20], [1, 21, 4], [2, 5, 55], [2, 18, 22], [3, 5, 19], [3, 21, 7], [4, 5, 43], [4, 22, 57], [5, 22, 28], [6, 21, 14]],
        'DW5_1':[[0, 14, 30], [1, 9, 29], [1, 15, 18], [2, 11, 10], [2, 18, 34], [3, 10, 39], [3, 16, 45], [4, 13, 54], [5, 15, 17], [6, 16, 13]],
        'DW5_0':[[0, 19, 30], [1, 15, 29], [1, 20, 18], [2, 18, 10], [2, 23, 34], [3, 16, 39], [3, 20, 45], [4, 18, 54], [5, 20, 17], [6, 22, 13]],
        }

    for i in range(5):
        for s, e in zip(dict_sched_dishwasher[f'DW{i+1}_1'], dict_sched_dishwasher[f'DW{i+1}_0']):
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            idx2 = int((e[0]*24*60) + (e[1]*60) + (e[2]))
            duration = (idx2 - idx)*60*1e-5
            
            while df_schedule.loc[idx, f'P{i+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{i+1}'] = 4 + (duration)  # 4 is the code number for dishwasher
            indices.append(idx)
        
    ### clotheswasher schedule
    dict_sched_clotheswasher = {    
        'CW1_1':[[0, 18, 58], [1, 12, 55],  [3, 17, 52], [3, 20, 32], [4, 10, 22], [5, 16, 15], [6, 14, 23]],
        'CW1_0':[[0, 21, 58], [1, 16, 55],  [3, 20, 55], [3, 22, 55], [4, 15, 22], [5, 19, 15], [6, 22, 23]],
        
        'CW2_1':[[2, 11, 35], [3, 7, 47], [5, 12, 27], [5, 16, 6], [5, 19, 45], [6, 14, 27]],
        'CW2_0':[[2, 14, 15], [3, 10, 27], [5, 15, 7], [5, 20, 6], [5, 22, 25], [6, 17, 7]],
        
        'CW3_1':[[0, 9, 23], [0, 13, 12], [2, 15, 35], [3, 12, 37], [3, 18, 17]],
        'CW3_0':[[0, 12, 3], [0, 16, 12], [2, 18, 35], [3, 15, 37], [3, 21, 17]],
        
        'CW4_1':[[0, 15, 19], [1, 11, 48], [2, 12, 39], [2, 19, 42], [3, 13, 5], [4, 10, 8], [4, 19, 32], [5, 14, 37], [6, 14, 54]],
        'CW4_0':[[0, 18, 19], [1, 14, 48], [2, 15, 39], [2, 22, 42], [3, 16, 5], [4, 13, 8], [4, 22, 32], [5, 17, 37], [6, 17, 54]],
        
        'CW5_1':[[0, 14, 12], [2, 13, 34], [3, 18, 55], [6, 18, 7]],
        'CW5_0':[[0, 17, 12], [2, 16, 34], [3, 21, 55], [6, 21, 7]],
        
        'CW6_1':[[2, 14, 8], [5, 15, 24]],
        'CW6_0':[[2, 17, 8], [5, 18, 24]],    
        }


            
    for i in range(5):
        for s, e in zip(dict_sched_clotheswasher[f'CW{i+1}_1'], dict_sched_clotheswasher[f'CW{i+1}_0']):
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            idx2 = int((e[0]*24*60) + (e[1]*60) + (e[2]))
            duration = (idx2 - idx)*60*1e-5
            
            while df_schedule.loc[idx, f'P{i+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{i+1}'] = 6 + (duration)
            indices.append(idx)

    ### clothesdryer
    dict_sched_clothesdryer = {
            'CD1_1':[[0, 21, 59], [1, 16, 59],  [3, 20, 59], [3, 22, 57], [4, 15, 25], [5, 19, 20], [6, 22, 28]],
            'CD1_0':[[0, 23, 58], [1, 18, 55],  [3, 22, 55], [3, 23, 55], [4, 17, 22], [5, 21, 15], [6, 23, 23]],
            
            'CD2_1':[[2, 14, 21], [3, 10, 32], [5, 15, 18], [5, 20, 15], [5, 22, 30], [6, 17, 12]],
            'CD2_0':[[2, 17, 15], [3, 13, 27], [5, 17, 7], [5, 22, 6], [5, 23, 55], [6, 19, 7]],
            
            'CD3_1':[[0, 12, 9], [0, 16, 18], [2, 18, 39], [3, 15, 47], [3, 21, 27]],
            'CD3_0':[[0, 14, 3], [0, 18, 12], [2, 20, 35], [3, 17, 37], [3, 23, 17]],
            
            'CD4_1':[[0, 18, 29], [1, 14, 58], [2, 15, 49], [2, 22, 52], [3, 16, 15], [4, 13, 18], [4, 22, 42], [5, 17, 47], [6, 17, 59]],
            'CD4_0':[[0, 20, 19], [1, 16, 48], [2, 17, 39], [2, 23, 52], [3, 18, 5], [4, 15, 8], [4, 23, 52], [5, 19, 37], [6, 19, 54]],
            
            'CD5_1':[[0, 17, 17], [2, 16, 44], [3, 21, 59], [6, 21, 17]],
            'CD5_0':[[0, 20, 12], [2, 18, 34], [3, 23, 55], [6, 23, 7]],
            
            'CD6_1':[[2, 17, 18], [5, 18, 34]],    
            'CD6_0':[[2, 20, 8], [5, 20, 24]],    

        }


    for i in range(5):
        for s, e in zip(dict_sched_clothesdryer[f'CD{i+1}_1'], dict_sched_clothesdryer[f'CD{i+1}_0']):
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            idx2 = int((e[0]*24*60) + (e[1]*60) + (e[2]))
            duration = (idx2 - idx) * 60 * 1e-5
            
            while df_schedule.loc[idx, f'P{i+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{i+1}'] = 5 + duration
            indices.append(idx)
            
            
    ### electric vehicles charging
    dict_sched_ev = {
        'EV1_1':[[0, 16, 30], [1, 16, 40], [2, 17, 0], [3, 16, 35], [4, 16, 53], [5, 18, 5], [6, 17, 13]],
        'EV1_0':[[1, 6, 30], [2, 5, 40], [3, 6, 0], [4, 5, 35], [5, 5, 53], [6, 8, 5], [7, 6, 13]],
        'EV2_1':[[0, 17, 20], [1, 17, 40], [2, 17, 10], [3, 17, 35], [4, 17, 53], [5, 19, 5], [6, 17, 13]],
        'EV2_0':[[1, 5, 20], [2, 5, 40], [3, 5, 10], [4, 5, 35], [5, 5, 53], [6, 9, 5], [7, 5, 13]],
        'EV3_1':[[0, 16, 25], [1, 16, 42], [2, 17, 10], [3, 16, 15], [4, 16, 23], [5, 17, 55], [6, 17, 33]],
        'EV3_0':[[1, 5, 25], [2, 4, 42], [3, 5, 10], [4, 5, 15], [5, 6, 23], [6, 6, 55], [7, 5, 33]],
        'EV4_1':[[0, 17, 13], [1, 17, 41], [2, 18, 3], [3, 17, 32], [4, 17, 43], [5, 18, 45], [6, 17, 43]],
        'EV4_0':[[1, 5, 13], [2, 5, 41], [3, 5, 3], [4, 5, 32], [5, 5, 43], [6, 6, 45], [7, 5, 43]],
        'EV5_1':[[0, 17, 48], [1, 18, 24], [2, 18, 30], [3, 18, 13], [4, 17, 23], [5, 18, 53], [6, 16, 13]],
        'EV5_0':[[1, 4, 48], [2, 4, 24], [3, 4, 30], [4, 4, 13], [5, 4, 23], [6, 4, 53], [7, 4, 13]],
        }


    for i in range(5):
        for s, e in zip(dict_sched_ev[f'EV{i+1}_1'], dict_sched_ev[f'EV{i+1}_0']):
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            idx2 = int((e[0]*24*60) + (e[1]*60) + (e[2]))
            duration = (idx2 - idx) * 60 * 1e-5
            
            while df_schedule.loc[idx, f'P{i+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{i+1}'] = 8 + duration
            indices.append(idx)
            
    #         code = df_schedule.loc[idx, f'P{i+1}']
    #         print(code, int((code-int(code))*1e5))

            
    ### heatpumps
    dict_sched_heatpump = {
        'HP1':[[0,7,13], [0,17,3], [1,7,2], [1,17,11], [2,7,17], [2,17,14], [3,7,15], [3,17,16], [4,7,17], [4,17,18], [5,7,4], [5,17,5], [6,7,6], [6,17,7]],  # morning_evening
        'HP2':[[0, 7, 5], [1, 7, 3], [2, 7, 5], [3, 7, 7],[4, 7, 9], [5, 7, 11], [6, 7, 13],],  # morning 7-9
        'HP3':[[0, 17, 17], [1, 17, 3], [2, 17, 2], [3, 17, 4], [4, 17, 6], [5, 17, 8], [6, 17, 10]],  # evening 17-23
        'HP4':[[0, 23, 2], [1, 23, 3], [2, 23, 4], [3, 23, 5], [4, 23, 6], [5, 23, 7], [6, 23, 8]],  # night 23-7
        'HP5':[[0, 0, 0], [0,7,1], [0,9,1], [0,17,1], [0,23,1], [1,7,1], [1,9,1], [1,17,1], [1,23,1], [2,7,1], [2,9,1], [2,17,1], [2,23,1], 
                [3,7,1], [3,9,1], [3,17,1], [3,23,1], [4,7,1], [4,9,1], [4,17,1], [4,23,1], [5,7,1], [5,9,1], [5,17,1], [5,23,1], 
                [6,7,1], [6,9,1], [6,17,1], [6,23,1]],  # 24 hours
        'HP6':[[0, 9, 2], [1, 9, 3], [2, 9, 4], [3, 9, 5], [4, 9, 6], [5, 9, 7], [6, 9, 8]],  # day 9-17
        }


    for i in range(5):
        for s in dict_sched_heatpump[f'HP{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            if s[1]==7:
                duration = (3600*2 + np.random.randint(-900,900)) * 1e-5
            elif s[1]==9:
                duration = (3600*8 + np.random.randint(-900,900)) * 1e-5
            elif s[1]==17:
                duration = (3600*6 + np.random.randint(-900,900)) * 1e-5
            elif s[1]==23:
                duration = (3600*8 + np.random.randint(-900,900)) * 1e-5
            else:
                duration = (3600*2 + np.random.randint(-900,900)) * 1e-5
                
            while df_schedule.loc[idx, f'P{i+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{i+1}'] = 11 + duration
            indices.append(idx)
            
    #         code = df_schedule.loc[idx, f'P{i+1}']
    #         print(code, int((code-int(code))*1e5))

            
    ### electric heaters
    dict_sched_heater = {
                'EH1':[[0,7,13], [0,17,3], [1,7,2], [1,17,11], [2,7,17], [2,17,14], [3,7,15], [3,17,16], [4,7,17], [4,17,18], [5,7,4], [5,17,5], [6,7,6], [6,17,7]],  # morning_evening
                'EH2':[[0, 7, 5], [1, 7, 3], [2, 7, 5], [3, 7, 7],[4, 7, 9], [5, 7, 11], [6, 7, 13],],  # morning 7-9
                'EH3':[[0, 17, 17], [1, 17, 3], [2, 17, 2], [3, 17, 4], [4, 17, 6], [5, 17, 8], [6, 17, 10]],  # evening 17-23
                'EH4':[[0, 23, 2], [1, 23, 3], [2, 23, 4], [3, 23, 5], [4, 23, 6], [5, 23, 7], [6, 23, 8]],  # night 23-7
                # 'EH5':[[0, 0, 0], [0,7,1], [0,9,1], [0,17,1], [0,23,1], [1,7,1], [1,9,1], [1,17,1], [1,23,1], [2,7,1], [2,9,1], [2,17,1], [2,23,1], 
                #         [3,7,1], [3,9,1], [3,17,1], [3,23,1], [4,7,1], [4,9,1], [4,17,1], [4,23,1], [5,7,1], [5,9,1], [5,17,1], [5,23,1], 
                #         [6,7,1], [6,9,1], [6,17,1], [6,23,1]],  # 24 hours
                'EH5':[[0, 9, 2], [1, 9, 3], [2, 9, 4], [3, 9, 5], [4, 9, 6], [5, 9, 7], [6, 9, 8]],  # day 9-17
        }

    for i in range(5):
        for s in dict_sched_heater[f'EH{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            if s[1]==7:
                duration = (3600*2 + np.random.randint(-900,900)) * 1e-5
            elif s[1]==9:
                duration = (3600*8 + np.random.randint(-900,900)) * 1e-5
            elif s[1]==17:
                duration = (3600*6 + np.random.randint(-900,900)) * 1e-5
            elif s[1]==23:
                duration = (3600*8 + np.random.randint(-900,900)) * 1e-5
            else:
                duration = (3600*2 + np.random.randint(-900,900)) * 1e-5
                
            while df_schedule.loc[idx, f'P{i+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{i+1}'] = 3 + duration
            indices.append(idx)
            
            

    ### cooking
    dict_sched_cooking = {
                'CK1':[[0, 7, 10], [0, 17, 34], [1, 13, 5], [2, 13, 17], [4, 0, 54], [4, 16, 4], [5, 9, 45], [5, 17, 25], [6, 11, 10], [6, 18, 20]],
                'CK2':[[0, 7, 15], [0, 17, 4], [1, 7, 59], [1, 19, 50], [2, 7, 59], [2, 18, 26], [3, 7, 29], [3, 18, 25], [4, 12, 32], [6, 7, 45]],
                'CK3':[[0, 14, 31], [1, 14, 45], [2, 17, 17], [2, 18, 55], [3, 12, 7], [3, 16, 1], [3, 21, 7], [5, 15, 11], [5, 22, 27], [6, 13, 33]],
                'CK4':[[0, 2, 7], [0, 14, 56], [1, 19, 27], [2, 20, 50], [3, 14, 22], [5, 0, 16], [5, 12, 14], [6, 12, 50], [6, 20, 20]],
                'CK5':[[0, 7, 39], [0, 21, 36], [1, 11, 53], [1, 19, 32], [3, 9, 28], [3, 20, 32], [4, 18, 10], [5, 19, 51], [6, 12, 39], [6, 19, 31]],
                'CK6':[[0, 17, 4], [2, 11, 56]],
                'CK7':[[0, 19, 16], [2, 8, 35]],
                'CK8':[[0, 12, 9], [1, 11, 53], [1, 20, 47], [2, 10, 14], [2, 18, 16], [2, 21, 34], [4, 16, 28], [5, 14, 31], [6, 15, 14], [6, 20, 55]],
                'CK9':[[0, 10, 44], [1, 10, 29], [2, 11, 12], [2, 20, 29], [3, 10, 2], [4, 11, 3], [5, 7, 17], [5, 11, 36], [5, 19, 58], [6, 11, 6]],
                'CK10':[[0, 8, 5], [0, 19, 32], [2, 7, 56], [2, 8, 41], [2, 17, 29], [2, 19, 49], [3, 7, 34], [5, 11, 25], [5, 19, 19], [6, 19, 16]],
                'CK11':[[0, 18, 19], [1, 10, 29], [2, 8, 14], [3, 10, 28], [6, 10, 52]],
            }

    for i in range(len(list(dict_sched_cooking))):
        for s in dict_sched_cooking[f'CK{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            duration = (1800*1 + np.random.randint(-900,900)) * 1e-5
            duration_water = (10*1 + np.random.randint(-5,0)) * 1e-5
            
            # hot water valve
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 13+(duration_water)
            indices.append(idx)
            
            # cold water valve
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 14+(duration_water)
            indices.append(idx)
            
            
            # humidifiers
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 16 + duration
            indices.append(idx)
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 17 + duration
            indices.append(idx)
            
            # kitchen window
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 19 + (duration * 1.05)
            indices.append(idx)
            
             # kitchen blinds
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 30 + (duration * 1.1)
            indices.append(idx)
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 31 + (duration * 1.1)
            indices.append(idx)
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 32 + (duration * 1.1)
            indices.append(idx)
            

    dict_sched_showers = {
         ## mornings and evenings
        'SH1':[[0, 8, 3], [0, 9, 35], [0, 20, 3], [0, 20, 30], [0, 21, 5], [0, 7, 3], 
               [1, 7, 35], [1, 9, 3],  [1, 20, 5], [1, 20, 38], [1, 21, 35], [1, 7, 5], 
               [2, 8, 3], [2, 9, 35], [2, 20, 3], [2, 20, 30], [2, 21, 5], [2, 7, 3],
               [3, 7, 35], [3, 9, 3], [3, 20, 5], [3, 20, 38], [3, 21, 35],  [3, 7, 5], 
               [4, 8, 3], [4, 9, 35], [4, 20, 3], [4, 20, 30], [4, 21, 5], [4, 7, 3],
               [5, 7, 35], [5, 9, 3], [5, 20, 5], [5, 20, 38], [5, 21, 35], [5, 7, 5], 
               [6, 7, 35], [6, 9, 3], [6, 20, 5], [6, 20, 38], [6, 21, 35], [6, 7, 5], 
               ], 
        ### mornings
        'SH2':[[0, 7, 3], [0, 7, 35], [0, 8, 3], [0, 9, 35],
               [1, 6, 25], [1, 7, 5], [1, 7, 35],[1, 9, 3], 
               [2, 6, 17], [2, 7, 3], [2, 8, 3], [2, 9, 35],
               [3, 6, 19], [3, 7, 5], [3, 7, 35],[3, 9, 3],
               [4, 6, 21], [4, 7, 3], [4, 8, 3], [4, 9, 35],
               [5, 8, 23], [5, 7, 5], [5, 7, 35],[5, 9, 3],
               [6, 7, 53], [6, 7, 5], [6, 7, 35],[6, 9, 3]
               ],
        ### evenings
        'SH3':[[0, 20, 3], [0, 20, 30], [0, 21, 5], [0, 21, 37], 
               [1, 22, 53], [1, 20, 5], [1, 20, 38], [1, 21, 35], 
               [2, 20, 37], [2, 20, 3], [2, 20, 30], [2, 21, 5],
               [3, 21, 29], [3, 20, 5], [3, 20, 38], [3, 21, 35], 
               [4, 21, 31], [4, 20, 3], [4, 20, 30], [4, 21, 5],
               [5, 21, 33], [5, 20, 5], [5, 20, 38], [5, 21, 35], 
               [6, 22, 33], [6, 20, 5], [6, 20, 38], [6, 21, 35]
               ],  
        ### less
        'SH4':[[0, 8, 35], [0, 21, 37],
               [1, 9, 3], [1, 20, 5],
               [2, 9, 35],[2, 20, 3],
               [3, 9, 3], [3, 20, 5],
               [4, 9, 35],[4, 20, 3],
               [5, 9, 3], [5, 20, 5], 
               [6, 9, 3], [6, 20, 5]],
        ### random
        'SH5':[[0, 10, 43], [0, 20, 43], 
               [1, 11, 46], [1, 14, 18], 
               [2, 10, 49], [2, 13, 49], 
               [3, 10, 49], [3, 13, 49], 
               [4, 10, 51], [4, 13, 51], 
               [5, 10, 34], [5, 14, 34], 
               [6, 10, 37], [6, 13, 37]],  
    }


    for i in range(len(list(dict_sched_showers))):
        for s in dict_sched_showers[f'SH{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            duration = (460.8 + np.random.randint(-245,245)) * 1e-5
            # duration = (460.8 + np.random.randint(-245, 0)) * 1e-5  # skewed to lower distribution to reduce water consumption at Ardmore
            
            '''
            Shower duration: avg=7.68 minutes, std=4.08min, median=7minutes
            Average hot water consumption
                Type of building    Consumption per occupant    Peak demand per occupant    Storage per occupant
                                    liter/day                   gal/day liter/hr        gal/hr  liter   gal
            Factories (no process)  22 - 45                         5 - 10                  9     2   5   1
            Hospitals, general      160                             35                      30  7   27  6
            Hospitals, mental       110                             25                      22  5   27  6
            Hostels                 90                              20                      45  10  30  7
            Hotels                  90 - 160                        20 - 35                 45  10  30  7
            Houses and flats        90 - 160                        20 - 35                 45  10  30  7
            Offices                 22                              5                       9   2   5   1
            Schools, boarding       115                             25                      20  4   25  5
            Schools, day            15                              3                       9   2   5   1
            
            Hence, valve flow is in average 90L/7.68*60s = 0.2L/s assuming that majority of the consumption is during shower and occupants only shower once a day
            '''

            # hot water valve
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 13+(duration*0.25) # half of the duration is hot, other half is cold
            indices.append(idx)
            
            # cold water valve
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 14+(duration*0.75)
            indices.append(idx)
            
            # bathroom windows
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 20+(duration*1.5)
            indices.append(idx)
            
            # bathroom doors
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 24+ (30*1e-5)  # get in
            indices.append(idx)
            
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx+int(duration*1e5*1.5), f'P{(i%5)+1}'] = 24+ (30*1e-5)  # get out
            indices.append(idx)
            
            
            
    #         code = df_schedule.loc[idx, f'P{i+1}']
    #         print(code, int((code-int(code))*1e5))

            
            
            
    dict_sched_windows = {
        'WD1':[[0, 9, 3], [1, 10, 5], [2, 10, 27], [3, 10, 9], [4, 10, 11], [5, 10, 13], [6, 13, 23]],
        'WD2':[[0, 9, 33], [1, 10, 25], [2, 10, 17], [3, 10, 19], [4, 10, 21], [5, 10, 23], [6, 13, 53]],
        'WD3':[[0, 9, 37], [1, 10, 53], [2, 10, 37], [3, 10, 29], [4, 10, 31], [5, 10, 33], [6, 13, 33]],
        'WD4':[[0, 9, 39], [1, 10, 42], [2, 10, 47], [3, 10, 39], [4, 10, 41], [5, 10, 31], [6, 13, 32]],
        'WD5':[[0, 9, 43], [1, 10, 46], [2, 10, 18], [3, 10, 49], [4, 10, 51], [5, 10, 34], [6, 13, 37]],
    }



    for i in range(len(list(dict_sched_windows))):
        for s in dict_sched_windows[f'WD{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            
            ### lounge windows
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 18 + (3600 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            ### room2 windows
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 21 + (3600 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            ### room1 windows
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 22 + (3600 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            


    dict_sched_doors = {
        'DR1':[[0, 7, 3], [0, 17, 3], [1, 7, 3], [1, 17, 3],[2, 7, 3], [2, 17, 3],[3, 7, 3], [3, 17, 3],
               [4, 7, 3], [4, 17, 3], [5, 7, 3], [5, 17, 3],[6, 7, 3], [6, 17, 3]],
        'DR2':[[0, 6, 33], [0, 17, 43], [1, 7, 25], [1, 16, 25], [2, 7, 17],[2, 17, 17], [3, 7, 19],[3, 16, 19], 
               [4, 10, 21], [4, 17, 21], [5, 7, 23],[5, 17, 23], [6, 6, 53], [6, 16, 53]],
        'DR3':[[0, 6, 37], [0, 17, 33], [1, 6, 53], [1, 16, 53], [2, 6, 37], [2, 16, 37], [3,7, 29],[3,16,29], 
               [4, 7, 31],[4, 17, 31], [5, 7, 33],[5, 16, 33], [6, 7, 33], [6, 16, 33]],
        'DR4':[[0, 6, 39], [0, 16, 31], [1,6,42],[1,16,42], [2,7,47],[2,16,47], [3,7,39],[3,16, 39], 
               [4, 7, 41],[4, 16, 41], [5, 7, 31],[5, 16, 31], [6, 7, 32], [6, 16, 32]],
        'DR5':[[0, 6, 43], [0, 17, 3], [1, 7, 46],[1, 16, 46], [2, 7, 18],[2, 16, 18], [3, 7, 49],[3, 16, 49], 
               [4, 6, 51],[4, 16, 51], [5, 7, 34],[5, 16, 34], [6, 7, 37],[6, 16, 37]],
    }  

    for i in range(len(list(dict_sched_doors))):
        for s in dict_sched_doors[f'DR{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            
            ### lounge door
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 23 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            ### room1 door
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 25 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            
            
    #         code = df_schedule.loc[idx, f'P{i+1}']
    #         print(code, int((code-int(code))*1e5))
            

    dict_sched_blinds = {
        'BD1':[[0, 7, 3], #[0, 17, 3], 
               [1, 7, 3], #[1, 17, 3],
               [2, 7, 3], #[2, 17, 3],
               [3, 7, 3], #[3, 17, 3],
               [4, 7, 3], #[4, 17, 3], 
               [5, 7, 3], #[5, 17, 3],
               [6, 7, 3]], #[6, 17, 3]],
        'BD2':[[0, 6, 33], #[0, 17, 43], 
               [1, 7, 25], #[1, 16, 25], 
               [2, 7, 17], #[2, 17, 17], 
               [3, 7, 19], #[3, 16, 19], 
               [4, 10, 21],#[4, 17, 21], 
               [5, 7, 23], #[5, 17, 23], 
               [6, 6, 53]], #[6, 16, 53]],
        'BD3':[[0, 6, 37], #[0, 17, 33], 
               [1, 6, 53], #[1, 16, 53], 
               [2, 6, 37], #[2, 16, 37], 
               [3,7, 29],  #[3,16,29], 
               [4, 7, 31], #[4, 17, 31], 
               [5, 7, 33], #[5, 16, 33], 
               [6, 7, 33]], #[6, 16, 33]],
        'BD4':[[0, 6, 39], #[0, 16, 31], 
               [1, 6, 42], #[1,16,42], 
               [2, 7, 47], #[2,16,47], 
               [3, 7, 39], #[3,16, 39], 
               [4, 7, 41], #[4, 16, 41], 
               [5, 7, 31], #[5, 16, 31], 
               [6, 7, 32]], #[6, 16, 32]],
        'BD5':[[0, 6, 43], #[0, 17, 3], 
               [1, 7, 46], #[1, 16, 46], 
               [2, 7, 18], #[2, 16, 18], 
               [3, 7, 49], #[3, 16, 49], 
               [4, 6, 51], #[4, 16, 51], 
               [5, 7, 34], #[5, 16, 34], 
               [6, 7, 37]],
    }  

    for i in range(len(list(dict_sched_blinds))):
        for s in dict_sched_blinds[f'BD{i+1}']:
            idx = int((s[0]*24*60) + (s[1]*60) + (s[2]))
            
            ### lounge partial blinds
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 2601 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 2603 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            ### room2 partial blinds
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 2608 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 2610 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            ### room1 partial blinds
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 2612 + (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
            
            while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
                idx = idx + 1
            df_schedule.loc[idx, f'P{(i%5)+1}'] = 2614+ (3600*3 + np.random.randint(-900,900)) * 1e-5
            indices.append(idx)
                    
            
            # ### all full blinds
            # while df_schedule.loc[idx, f'P{(i%5)+1}'] > 0: 
            #     idx = idx + 1
            # df_schedule.loc[idx, f'P{(i%5)+1}'] = 41 + (3600*13 + np.random.randint(-900,900)) * 1e-5
            # indices.append(idx)
            

    # print(df_schedule.loc[sorted(np.unique(indices))])
    return df_schedule

    # df_schedule.to_csv('./specs/schedules.csv', index=False, mode='w')
    # df_schedule.to_json('schedules.json', orient='index')
            

    '''
    [ (day, hour), (day, hour) ], 0=monday
    Clotheswasher:
    [(5, 15.877417240248917), (1, 12.12140059775325), (4, 12.269588777995011), (6, 15.212693156733678), (2, 15.068812034739452), (0, 17.569278514244715), (3, 17.10266332536898)]
    [(0, 13.466232513266021), (3, 11.767288080159233), (5, 15.877417240248917), (6, 15.212693156733678), (1, 13.758187058466532), (4, 12.269588777995011), (2, 15.068812034739452), (3, 19.691268158278376), (1, 4.755286103542474), (0, 20.43719350137185)]
    Dryer schedules:
    [(3, 19.3543031334183), (5, 13.608787691036753), (1, 21.25219945355191), (6, 21.474677486475173), (4, 17.597179974651468), (1, 12.627862688015426), (5, 11.088446121700542)]
    Dishwashers:
    model:995BAC
    [(1, 9, 4), (1, 9, 46), (1, 14, 16), (1, 14, 52), (4, 10, 54), (4, 11, 31), (5, 22, 11), (5, 22, 47), (6, 18, 24), (6, 18, 58)]
    model:B7E6F4
    [(0, 8, 43), (0, 9, 9), (0, 9, 30), (0, 9, 51), (0, 10, 16), (3, 9, 14), (3, 9, 51), (4, 8, 1), (4, 8, 26), (4, 8, 52)]
    model:B7E6FA
    [(0, 8, 45), (0, 21, 56), (1, 21, 21), (2, 12, 52), (3, 9, 11), (4, 8, 51), (4, 16, 57), (5, 20, 30), (6, 15, 26), (6, 21, 16)]
    model:B81D04
    [(0, 0, 20), (1, 15, 4), (2, 0, 55), (2, 11, 22), (2, 23, 19), (3, 16, 7), (4, 0, 43), (4, 17, 57), (5, 17, 28), (6, 15, 14)]
    model:B82F81
    [(0, 14, 30), (1, 9, 29), (1, 15, 18), (2, 11, 10), (2, 18, 34), (3, 9, 51), (3, 16, 12), (4, 13, 54), (5, 15, 17), (6, 16, 13)]

    Microwave:
    [(2, 18.16937371197065), (6, 14.989240627389904), (1, 15.798844884487956), (4, 18.412676340185314), (0, 11.813427331887127), (3, 16.918143519833393), (5, 16.40301999149284)]
    [(0, 11.813427331887127), (5, 16.40301999149284), (2, 18.183436505438678), (6, 19.945868945868995), (3, 20.63033250207816), (1, 19.914630512514982), (4, 18.443788736189617), (1, 12.385710659898116), (6, 13.169390690377384), (3, 12.097756620704757)]
    

    '''




# ## --- test create_fridgeSpecs ---
# df_houseSpecs = create_houseSpecs(n_houses=20, ldc_adoption=0.5, pv_adoption=0, wind_adoption=0, renew=True, report=False)
# create_windSpecs(n_winds=20, ldc_adoption=1.0, df_houseSpecs=df_houseSpecs, renew=True, report=True)
# ## end test





# #--create houses---
# def create_houses(houses_idx, df_houseSpecs, timescale):
#     try:
#         for i in houses_idx:   
#             HOUSE.House(name=str(df_houseSpecs.loc[[i],'name'].values[0]), 
#                 phase=df_houseSpecs.loc[[i],'phase'].values[0], 
#                 latitude=df_houseSpecs.loc[[i],'latitude'].values[0], 
#                 longitude=df_houseSpecs.loc[[i],'longitude'].values[0], 
#                 elevation=df_houseSpecs.loc[[i],'elevation'].values[0], 
#                 albedo=df_houseSpecs.loc[[i],'albedo'].values[0], 
#                 roof_tilt=df_houseSpecs.loc[[i],'roof_tilt'].values[0],
#                 azimuth=df_houseSpecs.loc[[i],'azimuth'].values[0],
#                 floor_area=df_houseSpecs.loc[[i],'floor_area'].values[0],
#                 aspect_ratio=df_houseSpecs.loc[[i],'aspect_ratio'].values[0],
#                 ceiling_height=df_houseSpecs.loc[[i],'ceiling_height'].values[0],
#                 ratio_window_wall=df_houseSpecs.loc[[i],'ratio_window_wall'].values[0], 
#                 ratio_window_roof=df_houseSpecs.loc[[i],'ratio_window_roof'].values[0],
#                 coefficient_window_transmission=df_houseSpecs.loc[[i],'coefficient_window_transmission'].values[0], 
#                 glazing_shgc=df_houseSpecs.loc[[i],'glazing_shgc'].values[0], 
#                 R_roof=df_houseSpecs.loc[[i],'R_roof'].values[0], 
#                 R_floor=df_houseSpecs.loc[[i],'R_floor'].values[0], 
#                 R_window=df_houseSpecs.loc[[i],'R_window'].values[0], 
#                 air_density=df_houseSpecs.loc[[i],'air_density'].values[0], 
#                 air_heat_capacity=df_houseSpecs.loc[[i],'air_heat_capacity'].values[0], 
#                 mass_fraction_external_heat=df_houseSpecs.loc[[i],'mass_fraction_external_heat'].values[0], 
#                 mass_fraction_internal_heat=df_houseSpecs.loc[[i],'mass_fraction_internal_heat'].values[0], 
#                 thermal_mass_per_area=df_houseSpecs.loc[[i],'thermal_mass_per_area'].values[0], 
#                 coefficient_internal_surface=df_houseSpecs.loc[[i],'coefficient_internal_surface'].values[0], 
#                 schedule_skew=df_houseSpecs.loc[[i],'schedule_skew'].values[0],
#                 mass_change=df_houseSpecs.loc[[i],'mass_change'].values[0], 
#                 installed_lights=df_houseSpecs.loc[[i],'installed_lights'].values[0], 
#                 installed_appliance=df_houseSpecs.loc[[i],'installed_appliance'].values[0], 
#                 utilization=df_houseSpecs.loc[[i],'utilization'].values[0],
#                 occupancy=df_houseSpecs.loc[[i],'occupancy'].values[0],
#                 mcast_ip_local=df_houseSpecs.loc[[i], 'mcast_ip_local'].values[0],
#                 mcast_port_local=df_houseSpecs.loc[[i], 'mcast_port_local'].values[0],
#                 mcast_ip_global=df_houseSpecs.loc[[i], 'mcast_ip_global'].values[0],
#                 mcast_port_global=df_houseSpecs.loc[[i], 'mcast_port_global'].values[0],
#                 timescale=timescale, 
#                 )
#     except Exception as e:
#         print("Error CREATOR create_houses:", e)


# def create_heatpumps(heatpumps_idx, df_heatpumpSpecs, timescale):
#     try:
#         for i in heatpumps_idx:
#             dict_params = {}
#             for key in list(df_heatpumpSpecs):
#                 dict_params[key] = df_heatpumpSpecs.loc[i, key]
            
#             LOAD.Hvac(dict_params)

#     except Exception as e:
#         print("Error CREATOR create_heatpumps:", e)




# def create_freezers(freezers_idx, df_freezerSpecs, timescale):
#     #---create freezers
#     try:
#         for i in freezers_idx:
#             dict_params = {}
#             for key in list(df_freezerSpecs):
#                 dict_params[key] = df_freezerSpecs.loc[i, key]
            
#             LOAD.Freezer(dict_params)

#     except Exception as e:
#         print("Error CREATOR create_freezers:", e)



# def create_fridges(fridges_idx, df_fridgeSpecs, timescale):
#     #---create fridges
#     try:
#         for i in fridges_idx:
#             dict_params = {}
#             for key in list(df_fridgeSpecs):
#                 dict_params[key] = df_fridgeSpecs.loc[i, key]
            
#             LOAD.Fridge(dict_params)

            
#     except Exception as e:
#         print("Error CREATOR create_fridges:", e)


# def create_waterheaters(waterheaters_idx, df_waterheaterSpecs, timescale):
#     #---create waterheaters
#     try:
#         for i in waterheaters_idx:
#             dict_params = {}
#             for key in list(df_waterheaterSpecs):
#                 dict_params[key] = df_waterheaterSpecs.loc[i, key]
            
#             LOAD.Waterheater(dict_params)

#     except Exception as e:
#         print("Error CREATOR create_waterheaters:", e)


# def create_clotheswasher(nntcls_idx, df_nntclSpecs, timescale):
#     #---Create 
#     profiles = []
#     for m in list_clotheswasher:
#         profiles.append(nntcl['Clotheswasher'][m]) 

#     for i in nntcls_idx:
#         try:
#             dict_params = {}
#             for key in list(df_nntclSpecs):
#                 dict_params[key] = df_nntclSpecs.loc[i, key]
            
#             LOAD.Clotheswasher(dict_params, list_profiles=profiles)
#         except Exception as e:
#             print("Error create_clotheswasher:", e)

# def create_clothesdryer(nntcls_idx, df_nntclSpecs, timescale):
#     #---Create 
#     profiles = []
#     for m in list_clothesdryer:
#         profiles.append(nntcl['Clothesdryer'][m]) 

#     for i in nntcls_idx:
#         try:
#             dict_params = {}
#             for key in list(df_nntclSpecs):
#                 dict_params[key] = df_nntclSpecs.loc[i, key]
            
#             LOAD.Clothesdryer(dict_params, list_profiles=profiles)

#         except Exception as e:
#             print("Error create_clothesdryer:",e)


# def create_dishwasher(nntcls_idx, df_nntclSpecs, timescale):
#     #---Create 
#     profiles = []
#     for m in list_dishwasher:
#         profiles.append(nntcl['Dishwasher'][m]) 

#     for i in nntcls_idx:
#         try:

#             dict_params = {}
#             for key in list(df_nntclSpecs):
#                 dict_params[key] = df_nntclSpecs.loc[i, key]
            
#             LOAD.Dishwasher(dict_params, list_profiles=profiles)

#         except Exception as e:
#             print("Error create_dishwasher:",e)


# def create_evs(evs_idx, df_evSpecs, timescale):
#     #---Create Electric Vehicles
#     try:
#         for i in evs_idx:
#             EVEHICLE.ElectricVehicle(name=df_evSpecs.loc[i, 'name'], 
#                 house=df_evSpecs.loc[i, 'house'], 
#                 with_dr=df_evSpecs.loc[i, 'with_dr'], 
#                 with_v2g=df_evSpecs.loc[i, 'with_v2g'], 
#                 capacity=df_evSpecs.loc[i, 'capacity'], 
#                 charging_power=df_evSpecs.loc[i, 'charging_power'], 
#                 charging_efficiency=df_evSpecs.loc[i, 'charging_efficiency'],
#                 soc=df_evSpecs.loc[i, 'soc'], 
#                 charging_start=df_evSpecs.loc[i, 'charging_start'], 
#                 charging_finish=df_evSpecs.loc[i, 'charging_finish'], 
#                 travel_distance=df_evSpecs.loc[i, 'travel_distance'], 
#                 travel_time=df_evSpecs.loc[i, 'travel_time'], 
#                 km_per_kwh=df_evSpecs.loc[i, 'km_per_kwh'],
#                 mcast_ip_local=df_evSpecs.loc[i, 'mcast_ip_local'],
#                 mcast_port_local=df_evSpecs.loc[i, 'mcast_port_local'],
#                 mcast_ip_global=df_evSpecs.loc[i, 'mcast_ip_global'],
#                 mcast_port_global=df_evSpecs.loc[i, 'mcast_port_global'],
#                 timescale=timescale,
#                 )
#     except Exception as e:
#         print("Error CREATOR create_evs:", e)


# def create_storages(storages_idx, df_storageSpecs, timescale):
#     #---Create battery storage
#     try:
#         for i in storages_idx:
#             STORAGE.Storage(name=df_storageSpecs.loc[i, 'name'], 
#                 house=df_storageSpecs.loc[i, 'house'], 
#                 with_dr=df_storageSpecs.loc[i, 'with_dr'],  
#                 capacity=df_storageSpecs.loc[i, 'capacity'], 
#                 charging_power=df_storageSpecs.loc[i, 'charging_power'], 
#                 charging_efficiency=df_storageSpecs.loc[i, 'charging_efficiency'], 
#                 soc=df_storageSpecs.loc[i, 'soc'],
#                 mcast_ip_local=df_storageSpecs.loc[i, 'mcast_ip_local'],
#                 mcast_port_local=df_storageSpecs.loc[i, 'mcast_port_local'],
#                 mcast_ip_global=df_storageSpecs.loc[i, 'mcast_ip_global'],
#                 mcast_port_global=df_storageSpecs.loc[i, 'mcast_port_global'],
#                 timescale=timescale,
#                 )
#     except Exception as e:
#         print("Error CREATOR create_storages:", e)


# def create_pvs(pvs_idx, df_solarSpecs, timescale):
#     #---Create PVs
#     try:
#         for i in pvs_idx:
#             POWER.DER_Solar(name=df_solarSpecs.loc[i, 'name'], 
#                 house=df_solarSpecs.loc[i, 'name'], 
#                 pv_roof_area=df_solarSpecs.loc[i, 'name'], 
#                 installed_capacity=df_solarSpecs.loc[i, 'name'], 
#                 pv_efficiency=df_solarSpecs.loc[i, 'name'], 
#                 inverter_efficiency=df_solarSpecs.loc[i, 'name'],
#                 mcast_ip_local=df_solarSpecs.loc[i, 'mcast_ip_local'],
#                 mcast_port_local=df_solarSpecs.loc[i, 'mcast_port_local'],
#                 mcast_ip_global=df_solarSpecs.loc[i, 'mcast_ip_global'],
#                 mcast_port_global=df_solarSpecs.loc[i, 'mcast_port_global'],
#                 timescale=timescale,
#                 )
#     except Exception as e:
#         print("Error CREATOR create_pvs:", e)

# def create_winds(winds_idx, df_windSpecs, timescale):
#     #---Create wind turbines
#     try:
#         for i in winds_idx:
#             POWER.DER_Wind(name=df_windSpecs.loc[i, 'name'], 
#                 house=df_windSpecs.loc[i, 'house'], 
#                 efficiency=df_windSpecs.loc[i, 'efficiency'], 
#                 installed_capacity=df_windSpecs.loc[i, 'installed_capacity'],
#                 mcast_ip_local=df_windSpecs.loc[i, 'mcast_ip_local'],
#                 mcast_port_local=df_windSpecs.loc[i, 'mcast_port_local'],
#                 mcast_ip_global=df_windSpecs.loc[i, 'mcast_ip_global'],
#                 mcast_port_global=df_windSpecs.loc[i, 'mcast_port_global'],
#                 timescale=timescale,
#                 )
#     except Exception as e:
#         print("Error CREATOR create_winds:", e)


# def create_meter(houses_idx, df_houseSpecs, timescale):
#     #---Create power meters
#     for i in houses_idx:   
#         METER.EnergyMeter(house=str(df_houseSpecs.loc[[i],'name'].values[0]), 
#             IDs=[0], autorun=True)


def create_specs(n_houses, n_heatpumps, n_heaters, n_waterheaters, n_fridges, n_freezers,
    n_evs, n_storages, n_clotheswashers, n_clothesdryers, n_dishwashers,
    n_pvs, n_winds, ldc_adoption, latitude, longitude, v2g_adoption=0, renew=0):

    try:
        df_houseSpecs = create_houseSpecs(n_houses, ldc_adoption, latitude=latitude, longitude=longitude, renew=renew)
        df_heatpumpSpecs = create_heatpumpSpecs(n_heatpumps, ldc_adoption, df_houseSpecs, renew=renew)
        df_heaterSpecs = create_heaterSpecs(n_heaters, ldc_adoption, df_houseSpecs, renew=renew)
        df_freezerSpecs = create_freezerSpecs(n_freezers, ldc_adoption, df_houseSpecs, renew=renew)
        df_fridgeSpecs = create_fridgeSpecs(n_fridges, ldc_adoption, df_houseSpecs, renew=renew)
        df_waterheaterSpecs = create_waterheaterSpecs(n_waterheaters, ldc_adoption, df_houseSpecs, renew=renew)
        # df_nntclSpecs = create_nntclSpecs(n_nntcls, ldc_adoption, df_houseSpecs, renew=renew)
        df_clotheswasherSpecs = create_clotheswasherSpecs(n_clotheswashers, ldc_adoption, df_houseSpecs, renew=renew)
        df_clothesdryerSpecs = create_clothesdryerSpecs(n_clothesdryers, ldc_adoption, df_houseSpecs, renew=renew)
        df_dishwasherSpecs = create_dishwasherSpecs(n_dishwashers, ldc_adoption, df_houseSpecs, renew=renew)
        df_evSpecs = create_evSpecs(n_evs, ldc_adoption, v2g_adoption, df_houseSpecs, renew=renew)
        df_storageSpecs = create_storageSpecs(n_storages, ldc_adoption, df_houseSpecs, renew=renew)
        df_solarSpecs = create_pvSpecs(n_pvs, ldc_adoption, df_houseSpecs, renew=renew)
        df_windSpecs = create_windSpecs(n_winds, ldc_adoption, df_houseSpecs, renew=renew)
        df_schedule =  create_schedules(renew=renew, report=False)
        df_schedule.to_csv('./specs/schedules.csv', index=False, mode='w')

        df_houseSpecs.to_hdf('./specs/device_specs.h5', key='house', mode='w', append=True, complib='blosc')
        df_heaterSpecs.to_hdf('./specs/device_specs.h5', key='heater', mode='a', append=True, complib='blosc')
        df_heatpumpSpecs.to_hdf('./specs/device_specs.h5', key='heatpump', mode='a', append=True, complib='blosc')
        df_waterheaterSpecs.to_hdf('./specs/device_specs.h5', key='waterheater', mode='a', append=True, complib='blosc')
        df_freezerSpecs.to_hdf('./specs/device_specs.h5', key='freezer', mode='a', append=True, complib='blosc')
        df_fridgeSpecs.to_hdf('./specs/device_specs.h5', key='fridge', mode='a', append=True, complib='blosc')
        df_clotheswasherSpecs.to_hdf('./specs/device_specs.h5', key='clotheswasher', mode='a', append=True, complib='blosc')
        df_clothesdryerSpecs.to_hdf('./specs/device_specs.h5', key='clothesdryer', mode='a', append=True, complib='blosc')
        df_dishwasherSpecs.to_hdf('./specs/device_specs.h5', key='dishwasher', mode='a', append=True, complib='blosc')
        df_evSpecs.to_hdf('./specs/device_specs.h5', key='ev', mode='a', append=True, complib='blosc')
        df_storageSpecs.to_hdf('./specs/device_specs.h5', key='storage', mode='a', append=True, complib='blosc')
        df_solarSpecs.to_hdf('./specs/device_specs.h5', key='solar', mode='a', append=True, complib='blosc')
        df_windSpecs.to_hdf('./specs/device_specs.h5', key='wind', mode='a', append=True, complib='blosc')

        print("Saved all specs in ./specs/device_specs.h5")

    except Exception as e:
        print("Error get df Specs:", e)




def main_func(plot=False, new_specs=[], justEV=False,
    n_houses=60,
    heatpump_per_house = 1.0,
    heater_per_house = 1.0,
    freezer_per_house = 1.3, 
    fridge_per_house= 1.3,
    waterheater_per_house=0.9, 
    nntcl_per_house=3,
    clotheswasher_per_house=0.9,
    clothesdryer_per_house=0.9,
    dishwasher_per_house=0.9,
    ev_per_house=0.3,
    storage_per_house=0.0,
    ldc_adoption=0.4,
    ev_ldc = 1.0,
    v2g_adoption = 0.0,
    solar_adoption = 0.0,
    wind_adoption = 0.0,
    grid_capacity = 300e3,
    step_size = 1,
    realtime = False,
    timescale = 1,
    three_phase = False,
    latitude = -36.86667, 
    longitude = 174.76667,
    simulate=0,
    renew=0):

    ############### INITIALIZATIONS ########################################################################
    #---web key for map api and weather api
    # try:
    #     latitude, longitude = FUNCTIONS.get_coordinates(query='79 Mullins Road, Ardmore, Papakura, New Zealand', report=False)
    # except Exception as e:
    #     latitude = -36.86667 
    #     longitude = 174.76667
    #     print("Using default coordinate:", latitude, longitude)


    # # run universal clock
    # CLOCK.Clock(name='global_clock', start=time.time(), end=None, step_size=step_size, realtime=realtime, timescale=timescale)

    local_ip = FUNCTIONS.get_local_ip()

    # adjust timezone setting used for runtime
    timezone = FUNCTIONS.get_timezone(latitude, longitude, timestamp=time.time())
    os.environ['TZ'] = timezone
    time.tzset()

    #---number of loads
    n_heatpumps = int(n_houses * heatpump_per_house)
    n_heaters = int(n_houses * heater_per_house)
    n_freezers = int(n_houses * freezer_per_house)
    n_fridges = int(n_houses * fridge_per_house)
    n_waterheaters = int(n_houses * waterheater_per_house)
    n_nntcls = int(n_houses * nntcl_per_house) 
    n_clotheswashers = int(n_houses * clotheswasher_per_house) 
    n_clothesdryers = int(n_houses * clothesdryer_per_house) 
    n_dishwashers = int(n_houses * dishwasher_per_house) 
    n_evs = int(n_houses * ev_per_house)
    n_storages = int(n_houses * storage_per_house)
    n_pvs = int(n_houses * solar_adoption)
    n_winds = int(n_houses * wind_adoption)

    print("Creating {} heatpumps, {} heaters, {} freezers, {} fridges, {} waterheaters, {} nntcl, {} clotheswasher, {} clothesdryer, {} dishwasher, {} ev, {} storage, {} pv, {} wind".format(n_heatpumps, 
        n_heaters, n_freezers, n_fridges, n_waterheaters, n_nntcls, n_clotheswashers, 
        n_clothesdryers, n_dishwashers, n_evs, n_storages, n_pvs, n_winds))    

    create_specs(n_houses=n_houses, n_heatpumps=n_heatpumps, n_heaters=n_heaters, 
        n_waterheaters=n_waterheaters, n_fridges=n_fridges, n_freezers=n_freezers,
        n_evs=n_evs, n_storages=n_storages, n_clotheswashers=n_clotheswashers, 
        n_clothesdryers=n_clothesdryers, n_dishwashers=n_dishwashers,
        n_pvs=n_pvs, n_winds=n_winds, ldc_adoption=ldc_adoption, 
        latitude=latitude, longitude=longitude, 
        v2g_adoption=v2g_adoption, renew=renew)
    
    return






# --------------------------------------------------------------------------------------
from optparse import OptionParser
import sys

if __name__=='__main__':
    parser = OptionParser(version=' ')
    parser.add_option('-n', '--n', dest='n_houses',
                    default=300, help='number of units')
    parser.add_option('-t', '--t', dest='timescale',
                    default=1, help='timescale')
    parser.add_option('-s', '--s', dest='simulate',
                    default=0, help='simulate')
    parser.add_option('-r', '--r', dest='renew',
                    default=1, help='renew')
    
    
    options, args = parser.parse_args(sys.argv[1:])
    print(options)
    # while True:
    try:
        n_houses = int(options.n_houses)
        simulate = int(options.simulate)
        renew = int(options.renew)

        gridUtilizationFactor =  0.8**(0.9 * np.log(n_houses))
        grid_capacity = n_houses * 10000 * gridUtilizationFactor     

        main_func(plot=False, new_specs=[], justEV=False,
            n_houses=n_houses,
            heatpump_per_house=1.0,
            heater_per_house=1.0,
            freezer_per_house=1.0, #1.3, 
            fridge_per_house=1.0, #1.3,
            waterheater_per_house=1.0, #0.9, 
            nntcl_per_house=1.0,#3,
            clotheswasher_per_house=1, #0.9,
            clothesdryer_per_house=1, #0.9,
            dishwasher_per_house=1, #0.9,
            ev_per_house=1.0, #0.3,
            storage_per_house=1.0, #0.5,
            ldc_adoption=1.0,
            ev_ldc=1.0,
            v2g_adoption=0.0,
            solar_adoption = 1.0,
            wind_adoption = 1.0,
            grid_capacity = grid_capacity,
            step_size = 1,
            realtime = True,
            timescale = 1,
            three_phase = True,
            latitude = -36.86667, 
            longitude = 174.76667,
            simulate=simulate,
            renew=renew)

    except Exception as e:
        print("Error main:", e)

