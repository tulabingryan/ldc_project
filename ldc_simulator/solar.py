#############################################################
# Codes for simulating a Solar PV model
# by: Ryan Tulabing
# Lawrence Berkeley National Laboratory
# Berkeley, California
# Feb. 2015 - Aug. 2015
#############################################################


import time
import datetime
import numpy as np
import pandas as pd
import glob


# GLOBAL CONSTANTS
Gsc = 1367.0  # W/m^2, solar energy per unit time per area beyond the atmosphere
albedo = 0.2  # reflection coefficient of the surroundings. Common value is 0.2
e = np.e  # 2.718281828459045  # euler's number
pi = np.pi  # 3.141592653589793  # pi constant


        

# FUNCTIONS USED

def get_yday(**kwargs):
    # This function returns which day of the year is the specific date 'when'
    try:
        kwargs['when'] = time.localtime(kwargs['unixtime'])
        kwargs['yday'] = kwargs['when'][7]
    except Exception as e:
        print("Error solar get_yday:",e)
    return kwargs

### test 
# dict_vars = get_yday(**dict_vars)


def get_climate_type(**kwargs):
    # This function returns the type climate in a certain area based solely on its latitude
    # The climate types considered are the types of climate for predicting solar irradiance, by Hottel (1976)
    try:
        kwargs['is_summer'] = kwargs['when'][8]

        idx1 = np.flatnonzero((np.abs(kwargs['latitude'])<=23.5))
        idx2 = np.flatnonzero((np.abs(kwargs['latitude'])>23.5)&(np.abs(kwargs['latitude'])<=66.5)&(kwargs['is_summer']==1))
        idx3 = np.flatnonzero((np.abs(kwargs['latitude'])>23.5)&(np.abs(kwargs['latitude'])<=66.5)&(kwargs['is_summer']==0))
        idx4 = np.flatnonzero((np.abs(kwargs['latitude'])>66.5))
        
        kwargs['climate_type'] = np.ones(kwargs['latitude'].shape)
        kwargs['climate_type'][idx1] = 0  # tropical
        kwargs['climate_type'][idx2] = 1  # Midlatitude summer
        kwargs['climate_type'][idx3] = 3  # Midlatitude winter
        kwargs['climate_type'][idx4] = 2  # Subarctic summer
    except Exception as e:
        print("Error solar get_climate_type:", e)
    return kwargs


# ### test 
# dict_vars = get_climate_type(**dict_vars)



def get_solar_time(**kwargs):
    # This function converts a given time from its local timezone into the equivalent solar time.
    try:
        B = np.multiply(np.subtract(kwargs['yday'],1), (360.0/365.0))
        # time equation, E, Spencer(1971), Iqbal(1983)
        E = 229.2*(0.000075+(0.001868*np.cos(np.radians(B)))-(0.032077*np.sin(np.radians(B)))\
                    - (0.014615*np.cos(2*np.radians(B)))-(0.04089*np.sin(2*np.radians(B))))

        kwargs['isotime'] = datetime.datetime.fromtimestamp(kwargs['unixtime']).isoformat()
        kwargs['meridian'] = np.ones(kwargs['longitude'].shape) * np.multiply(15, np.divide(time.timezone, 3600))
        
        idx1 = np.flatnonzero(kwargs['longitude']>0)
        idx2 = np.flatnonzero(kwargs['longitude']<=0)

        kwargs['meridian'][idx1] = np.add(360, kwargs['meridian'][idx1])
        longitude_adjusted = kwargs['longitude'].copy()
        
        longitude_adjusted[idx1] = np.subtract(360, kwargs['longitude'][idx1])
        longitude_adjusted[idx2] = np.abs(kwargs['longitude'][idx2])

        kwargs['minute_diff'] = np.array((4*(kwargs['meridian']-longitude_adjusted))+E).astype('timedelta64[m]')  # time difference in minutes
        
        kwargs['solar_time'] = np.add(np.datetime64(kwargs['isotime']), kwargs['minute_diff'])
        kwargs['solar_time'] = pd.to_datetime(kwargs['solar_time'], infer_datetime_format=True)
        
    except Exception as e:
        print("Error solar get_solar_time:", e)

    return kwargs

# ### test 
# dict_vars = get_solar_time(**dict_vars)


# #------test------------
# when = time.localtime(time.time())
# print(when)
# longitude = np.random.normal(118, 3, 10)
# x = get_solar_time(when, longitude)
# print(x)


def get_hour_angle(**kwargs):
    # Calculate the hour angle
    try:
        kwargs['solar_hour'] = np.add(kwargs['solar_time'].hour, np.add(np.divide(kwargs['solar_time'].minute,60.0), np.divide(kwargs['solar_time'].second, 3600.0)))
        # hour angle is the displacement of the sun east or west of the observer's meridian
        # It is 15 degrees per hour, negative values for morning, positive for afternoon
        kwargs['hour_angle'] = np.array(np.multiply(np.subtract(kwargs['solar_hour'], 12.0), 15.0))  # 15 degrees per hour movement of the sun
    except Exception as e:
        print("Error solar get_hour_angle:", e)

    return kwargs


# ### test 
# dict_vars = get_hour_angle(**dict_vars)



# #------test---------------
# when = time.localtime(time.time())
# longitude = np.random.normal(118, 3, 10)
# x = get_hour_angle(when, longitude)
# print(x)




def get_declination(**kwargs):
    # Calculate the angle of declination
    try: 
        B = (kwargs['yday']-1)*(360.0/365.0)
        # solar declination angle, Spencer(1971)... more accurate
        kwargs['declination'] = (180/pi)*(0.006918-(0.399912*np.cos(np.radians(B)))+(0.070257*np.sin(np.radians(B)))\
                                - (0.006758*np.cos(2*np.radians(B)))+(0.000907*np.sin(2*np.radians(B)))\
                                - (0.002697*np.cos(3*np.radians(B)))+(0.00148*np.sin(3*np.radians(B))))
        # if estimated value is preferred, uncomment the following lines
        #kwargs['declination'] = 23.45*np.sin(np.radians(360.0*(284+kwargs['yday'])/365))  # approximate version, Cooper(1969)
    except Exception as e:
        print("Error solar get_declination:", e)
    return kwargs

# ### test 
# dict_vars = get_declination(**dict_vars)



###---------test-----------------
# when = time.localtime(time.time())
# longitude = np.random.normal(118, 3, 10)
# x = get_declination(when)
# print(x)



def get_sunset_hour_angle(**kwargs):
    # Calculate the sunset hour angle
    try:
        a = np.tan(np.radians(kwargs['latitude']))
        b = np.tan(np.radians(kwargs['declination']))
        kwargs['sunset_hour_angle'] = np.arccos(-1 * a * b)  # Duffie & Beckman(2013)
        kwargs['sunset_hour_angle'] = np.degrees(kwargs['sunset_hour_angle'])
    except Exception as e:
        print("Error solar get_sunset_hour_angle:", e)
    return kwargs

# ### test 
# dict_vars = get_sunset_hour_angle(**dict_vars)



###------------test--------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# x = get_sunset_hour_angle(when, latitude)
# print(x)



def get_sunrise_hour_angle(**kwargs):
    # Calculate the sunrise hour angle
    try:
        kwargs['sunrise_hour_angle'] = -1.0 * kwargs['sunset_hour_angle']  # Duffie & Beckman(2013)    
    except Exception as e:
        print("Error solar get_sunrise_hour_angle")
    
    return kwargs

# ### test 
# dict_vars = get_sunrise_hour_angle(**dict_vars)



def get_zenith_angle(**kwargs):
    # Calculate the zenith angle
    
    # idx1 = np.flatnonzero((kwargs['sunrise_hour_angle']<=kwargs['hour_angle'])&(kwargs['hour_angle']<=kwargs['sunset_hour_angle']))
    # idx2 = np.flatnonzero((kwargs['sunrise_hour_angle']>kwargs['hour_angle'])|(kwargs['hour_angle']>kwargs['sunset_hour_angle']))
    try:
        cos_lat = np.cos(np.radians(kwargs['latitude']))
        cos_dec = np.cos(np.radians(kwargs['declination']))
        cos_w = np.cos(np.radians(kwargs['hour_angle']))
        sin_lat = np.sin(np.radians(kwargs['latitude']))
        sin_dec = np.sin(np.radians(kwargs['declination']))

        kwargs['zenith_angle'] = np.clip(np.degrees(np.arccos(np.add(np.multiply(cos_lat, np.multiply(cos_dec, cos_w)), np.multiply(sin_lat, sin_dec)))), a_min=0, a_max=90).reshape(kwargs['longitude'].shape)  # Duffie & Beckman(2013)

    except Exception as e:
        print("Error solar get_zenith_angle:", e)
    
    return kwargs

# ### test 
# dict_vars = get_zenith_angle(**dict_vars)



###------------test--------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# x = get_zenith_angle(when, latitude, longitude)
# print(x)



def get_solar_altitude(**kwargs):
    # Calculate the solar elevation angle
    try:
        kwargs['solar_altitude'] = 90.0 - kwargs['zenith_angle']    
    except Exception as e:
        print("Error solar get_solar_altitude:", e)
    
    return kwargs

# ### test 
# dict_vars = get_solar_altitude(**dict_vars)



def get_solar_azimuth(**kwargs):
    # Calculate the solar azimuth angle
    try:
        idx = np.flatnonzero(kwargs['hour_angle']==0)
        angleSign = np.sign(kwargs['hour_angle'])
        angleSign[idx] = 1

        a = np.cos(np.radians(kwargs['zenith_angle']))
        b = np.sin(np.radians(kwargs['latitude']))
        c = np.sin(np.radians(kwargs['declination']))
        d = np.sin(np.radians(kwargs['zenith_angle']))
        f = np.cos(np.radians(kwargs['latitude']))

        partial = np.clip((((a*b)-c)/(d*f)), a_min=-1, a_max=1)
        kwargs['solar_azimuth'] = angleSign * np.fabs(np.arccos(partial))  # Duffie & Beckman(2013)
        kwargs['solar_azimuth'] = np.clip(np.degrees(kwargs['solar_azimuth']), a_min=-180, a_max=180)    

    except Exception as e:
        print("Error solar get_solar_azimuth:", e)
    
    return kwargs

# ### test 
# dict_vars = get_solar_azimuth(**dict_vars)



# ###------------test--------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# x = get_solar_azimuth(when, latitude, longitude)
# print(x)





# ###------------test--------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# x = get_solar_altitude(when, latitude, longitude)
# print(x)


def get_incidence_angle(**kwargs):
    # Calculate the incidence angle
    try:
        a = np.cos(np.radians(kwargs['zenith_angle']))
        b = np.cos(np.radians(kwargs['tilt']))
        c = np.sin(np.radians(kwargs['zenith_angle']))
        d = np.sin(np.radians(kwargs['tilt']))
        f = np.cos(np.radians(np.subtract(kwargs['solar_azimuth'], kwargs['azimuth'])))

        kwargs['incidence_angle'] = np.arccos(np.add(np.multiply(a, b), np.multiply(c, np.multiply(d,f))))  # Duffie & Beckman(2013)
        kwargs['incidence_angle'] = np.array(np.degrees(kwargs['incidence_angle']))

        idx = np.flatnonzero((kwargs['hour_angle']<kwargs['sunrise_hour_angle'])|(kwargs['hour_angle']>kwargs['sunset_hour_angle']))
        kwargs['incidence_angle'][idx] = 180

    except Exception as e:
        print("Error solar get_incidence_angle:", e)
    return kwargs

# ### test 
# dict_vars = get_incidence_angle(**dict_vars)



# ###------------test--------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_incidence_angle(when, latitude, longitude, tilt, azimuth)
# print(x)



def get_daylight_hours(**kwargs):
    # Calculate the total daylight hours
    try:
        kwargs['daylight_hours'] = (2.0/15.0)*kwargs['sunset_hour_angle']  # Duffie & Beckman(2013)    
    except Exception as e:
        print("Error solar get_daylight_hours:", e)
    
    return kwargs

# ### test 
# dict_vars = get_daylight_hours(**dict_vars)


### ------test -----------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_daylight_hours(when, latitude)
# print(x)


def get_profile_angle(**kwargs):
    # Calculate the profile angle
    try:
        a = np.tan(np.radians(kwargs['solar_altitude']))
        b = np.cos(np.radians(kwargs['solar_azimuth'] - kwargs['azimuth']))
        kwargs['profile_angle'] = np.arctan(a / b)
        kwargs['profile_angle'] = np.degrees(kwargs['profile_angle'])    
    except Exception as e:
        print("Error solar get_profile_angle:", e)
    
    return kwargs


# ### test 
# dict_vars = get_profile_angle(**dict_vars)


### ------test -----------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_profile_angle(when, latitude, longitude, azimuth)
# print(x)


def get_sunset_hour(**kwargs):
    # Calculate the sunset hour
    try:
        kwargs['sunset_hour'] = np.add(np.divide(kwargs['sunset_hour_angle'], 15.0), 12.0)    
    except Exception as e:
        print("Error solar get_sunset_hour:", e)
    
    return kwargs

# ### test 
# dict_vars = get_sunset_hour(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_sunset_hour(when, latitude)
# print(x)



def get_sunrise_hour(**kwargs):
    # Calculate the sunrise hour
    try:
        kwargs['sunrise_hour'] = np.add(np.divide(kwargs['sunrise_hour_angle'], 15.0), 12.0)    
    except Exception as e:
        print("Error solar get_sunrise_hour:", e)
    
    return kwargs

# ### test 
# dict_vars = get_sunrise_hour(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_sunrise_hour(when, latitude)
# print(x)


def get_airmass(**kwargs):
    # airmass factor, Kaster and Young(1989)
    try:
        partial1 = np.power(np.e, np.multiply(-0.0001184, kwargs['elevation']))
        partial2 = np.add(np.cos(kwargs['zenith_angle']), np.multiply(0.5057, np.power(np.subtract(96.080, kwargs['zenith_angle']), (-1.634))))    
        kwargs['airmass'] = np.divide(partial1, partial2)

    except Exception as e:
        print("Error solar get_airmass:", e)
    
    return kwargs

# ### test 
# dict_vars = get_airmass(**dict_vars)





def get_one_day_solar(**kwargs):
    # Calculate the total solar energy in one day
    try:
        a = np.cos(np.radians(360.0 * kwargs['yday'] / 365.0))
        b = np.cos(np.radians(kwargs['latitude']))
        c = np.cos(np.radians(kwargs['declination']))
        d = np.sin(np.radians(kwargs['sunset_hour_angle']))
        f = np.sin(np.radians(kwargs['latitude']))
        g = np.sin(np.radians(kwargs['declination']))
        kwargs['oneday_solar'] = (24.0*3600*Gsc/np.pi)*(1+(0.033*a))*((b*c*d)+(np.pi*kwargs['sunset_hour_angle']*f*g/180)) # Joules / m^2 per day    
    except Exception as e:
        print("Error solar get_one_day_solar:", e)
    
    return kwargs

# ### test 
# dict_vars = get_one_day_solar(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_one_day_solar(when, latitude, longitude)
# print(x)



def get_outer_beam_normal(**kwargs):
    # this function gets the extraterrestrial solar irradiation on a normal plane considering the variations
    # in earth-sun distance throughout the year
    try:
        B = (kwargs['yday']-1) * (360.0/365.0)
        ones = np.ones(kwargs['longitude'].shape)
        a = np.multiply(ones, np.cos(np.radians(B)))
        b = np.multiply(ones,np.sin(np.radians(B)))
        c = np.multiply(ones, np.cos(2*np.radians(B)))
        d = np.multiply(ones, np.sin(2*np.radians(B)))

        #if (0 < sunriseDif < 15):
        #    outer_beam_normal =  ((sunriseDif)/15)*Gsc * (1.000110+(0.034221*a)+(0.001280*b) + (0.000719*c)+(0.000077*d))  # Iqbal(1983)
        #elif (0 < sunsetDif < 15):
        #    outer_beam_normal =  ((15 - sunsetDif)/15)*Gsc * (1.000110+(0.034221*a)+(0.001280*b) + (0.000719*c)+(0.000077*d))  # Iqbal(1983)

        n_idx = np.flatnonzero((kwargs['sunrise_hour_angle']>kwargs['hour_angle'])|(kwargs['hour_angle']>kwargs['sunset_hour_angle']))
        kwargs['outer_beam_normal'] = Gsc * (1.000110+(0.034221*a)+(0.001280*b) + (0.000719*c)+(0.000077*d))  # Iqbal(1983) # in W/m2
        # kwargs['outer_beam_normal'][n_idx] = 0.0

        # Below is the estimate version, less accurate
        #kwargs['outer_beam_normal'] = Gsc * (1 + (0.033* np.cos(np.radians(360.0*kwargs['yday']/365.0))))    
    except Exception as e:
        print("Error solar get_outer_beam_normal")
    
    return kwargs

### test
# dict_vars = get_outer_beam_normal(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time())
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_outer_beam_normal(when, latitude, longitude)
# print(x)


def get_outer_beam_horizontal(**kwargs):
    # This function gets the extraterrestrial solar irradiation on a horizontal plane considering the variations
    # in earth-sun distance throughout the year
    try:
        kwargs['outer_beam_horizontal'] = np.multiply(kwargs['outer_beam_normal'], np.cos(np.radians(kwargs['zenith_angle']))) # in W/m^2
        kwargs['outer_beam_horizontal'] = np.clip(kwargs['outer_beam_horizontal'], a_min=0, a_max=9999)

    except Exception as e:
        print("Error solar get_outer_beam_horizontal:", e)
    
    return kwargs

### test
# dict_vars = get_outer_beam_horizontal(**dict_vars)




# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_outer_beam_horizontal(when, latitude, longitude)
# print(x)


def get_clearsky_beam_horizontal(**kwargs):
    # This function calculates the direct beam irradiance during clears skies on a Horizontal plane
    # using the method developed by Hottel (1976)
    #    climate_type = 0 if tropical,1 if Midlatitude summer,2 if Subarctic summer,3 if Midlatitude winter
    try:
        a0 = 0.4237-(0.00821*((6.0-(kwargs['elevation']/1000.0))**2))
        a1 = 0.5055+(0.00595*((6.5-(kwargs['elevation']/1000.0))**2))
        k = 0.2711+(0.01858*((2.5-(kwargs['elevation']/1000.0))**2))
        
        # applying the correction factors based on climate type
        idx1 = np.flatnonzero((kwargs['climate_type']==0))
        idx2 = np.flatnonzero((kwargs['climate_type']==1))
        idx3 = np.flatnonzero((kwargs['climate_type']==2))
        idx4 = np.flatnonzero((kwargs['climate_type']==3))

        a0[idx1] = a0[idx1] * 0.95
        a1[idx1] = a1[idx1] * 0.98
        k[idx1] = k[idx1] * 1.02

        a0[idx2] = a0[idx2] * 0.97
        a1[idx2] = a1[idx2] * 0.99
        k[idx2] = k[idx2] * 1.02


        a0[idx3] = a0[idx3] * 0.99
        a1[idx3] = a1[idx3] * 0.99
        k[idx3] = k[idx3] * 1.01


        a0[idx4] = a0[idx4] * 1.03
        a1[idx4] = a1[idx4] * 1.01
        k[idx4] = k[idx4] * 1.0


        # idx = np.flatnonzero((np.sin(np.radians(kwargs['zenith_angle']))==0))
        # n_idx = np.flatnonzero((np.sin(np.radians(kwargs['zenith_angle']))!=0))

        # tau_b = a0
        # tau_b[n_idx] = a0[n_idx] + (a1[n_idx] * np.e**(-k[n_idx]/np.cos(np.radians(kwargs['zenith_angle'][n_idx]))))

        tau_b = a0 + (a1 * np.e**(-k/np.cos(np.radians(kwargs['zenith_angle']))))

        kwargs['clearsky_beam'] = np.cos(np.radians(kwargs['zenith_angle']))
        kwargs['clearsky_beam'] = np.multiply(kwargs['clearsky_beam'], tau_b)
        kwargs['clearsky_beam'] = np.multiply(kwargs['clearsky_beam'], kwargs['outer_beam_normal'])

        kwargs['clearsky_beam'] = (kwargs['outer_beam_normal'] * tau_b * np.cos(np.radians(kwargs['zenith_angle'])))  # Hottel (1976) [W/m^2]

    except Exception as e:
        print("Error solar get_clearsky_horizontal:", e)
    
    return kwargs


### test
# dict_vars = get_clearsky_beam_horizontal(**dict_vars)




# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x = get_clearsky_beam_horizontal(when, latitude, longitude, elevation)
# print(x)



def get_clearsky_diffused_horizontal(**kwargs):
    # This function calculates the diffused irradiance during clear skies on a horizontal plane
    # Returns the diffused irradiance during clear skies in W/m^2
    try:
        a0 = 0.4237-(0.00821*((6.0-(kwargs['elevation']/1000.0))**2))
        a1 = 0.5055+(0.00595*((6.5-(kwargs['elevation']/1000.0))**2))
        k = 0.2711+(0.01858*((2.5-(kwargs['elevation']/1000.0))**2))
        
        # applying the correction factors based on climate type
        idx1 = np.flatnonzero((kwargs['climate_type']==0))
        idx2 = np.flatnonzero((kwargs['climate_type']==1))
        idx3 = np.flatnonzero((kwargs['climate_type']==2))
        idx4 = np.flatnonzero((kwargs['climate_type']==3))

        a0[idx1] = a0[idx1] * 0.95
        a1[idx1] = a1[idx1] * 0.98
        k[idx1] = k[idx1] * 1.02

        a0[idx2] = a0[idx2] * 0.97
        a1[idx2] = a1[idx2] * 0.99
        k[idx2] = k[idx2] * 1.02


        a0[idx3] = a0[idx3] * 0.99
        a1[idx3] = a1[idx3] * 0.99
        k[idx3] = k[idx3] * 1.01


        a0[idx4] = a0[idx4] * 1.03
        a1[idx4] = a1[idx4] * 1.01
        k[idx4] = k[idx4] * 1.0

        # idx = np.flatnonzero((np.cos(np.radians(kwargs['zenith_angle']))==0))
        # n_idx = np.flatnonzero((np.cos(np.radians(kwargs['zenith_angle']))!=0))

        # tau_b = a0
        # tau_b[n_idx] = a0[n_idx] + (a1[n_idx] * np.e**(-k[n_idx]/np.cos(np.radians(kwargs['zenith_angle'][n_idx]))))

        tau_b = a0 + (a1 * np.e**(-k/np.cos(np.radians(kwargs['zenith_angle']))))

        Gcd = kwargs['outer_beam_horizontal'] * (0.271 - (0.294*tau_b))  # Liu and Jordan (1960)
        # Gcd[Gcd<0] = 0.0
        kwargs['clearsky_diffused'] = Gcd  

    except Exception as e:
        print("Error solar get_clearsky_diffused_horizontal:", e)
    
    return kwargs


### test
# dict_vars = get_clearsky_diffused_horizontal(**dict_vars)


# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x2 = get_clearsky_diffused_horizontal(when, latitude, longitude, elevation)
# print(x2)


def get_clearsky_horizontal(**kwargs):
    # This function determines the total clear sky horizontal irradiance
    try:
        kwargs['clearsky_horizontal'] = kwargs['clearsky_beam'] + kwargs['clearsky_diffused']    
    except Exception as e:
        print("Error solar get_clearsky_horizontal:", e)
    
    return kwargs


### test
# dict_vars = get_clearsky_horizontal(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)

# x2 = get_clearsky_horizontal(when, latitude, longitude, elevation)
# print(x2)


def get_clearness_index(**kwargs):
    # This function determines the clearness index
    # correlation equation was derived by another python code based on the tmy3 database
    try:
        kwargs['clearness_index'] = np.add(np.multiply(-4.0609675416664, np.multiply(1e-5, np.power(kwargs['humidity'], 2))), 
            np.add(np.multiply(-0.0013504072, kwargs['humidity']), 0.7546969703))   
        kwargs['clearness_index'] = np.clip(kwargs['clearness_index'], a_min=0, a_max=1)
    except Exception as e:
        print("Error solar get_clearness_index:", e)
    
    return kwargs

### test
# dict_vars = get_clearness_index(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)
# humidity = np.random.normal(0.3, 0.3, 10)
# x2 = get_Kt(humidity)
# print(x2)


def get_solar_ground(**kwargs):
    # Calculate the total solar beam (direct and diffused) at the ground level
    try:
        kwargs['irradiance_ground'] = kwargs['clearness_index'] * kwargs['outer_beam_horizontal']  
    except Exception as e:
        print("Error solar get_solar_ground:", e)
    
    return kwargs

### test
# dict_vars = get_solar_ground(**dict_vars)

# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)
# humidity = np.random.normal(0.3, 0.3, 10)
# x2 = get_G(when, latitude, longitude, humidity)
# print(x2)

def get_diffused_ground(**kwargs):
    # Calculate the diffused solar beam at the ground level
    try:
        # Orgill and Hollands correlation
        idx1 = np.flatnonzero(kwargs['clearness_index']<=0.35)
        idx2 = np.flatnonzero((kwargs['clearness_index']>0.35)&(kwargs['clearness_index']<=0.75))
        idx3 = np.flatnonzero(kwargs['clearness_index']>0.75)
        

        kwargs['diffused_ground'] = np.multiply(kwargs['irradiance_ground'], np.subtract(1.0, np.multiply(0.249, kwargs['clearness_index'])))  # idx1 is not used to create a 'diffused_ground' label in kwargs
        if np.size(idx2): kwargs['diffused_ground'][idx2] = np.multiply(kwargs['irradiance_ground'][idx2], np.subtract(1.557, np.multiply(1.84, kwargs['clearness_index'][idx2])))
        if np.size(idx3): kwargs['diffused_ground'][idx3] = np.multiply(kwargs['irradiance_ground'][idx3], 0.177)
            
    except Exception as e:
        print("Error solar get_diffused_ground:", e)
    return kwargs

### test
# dict_vars = get_diffused_ground(**dict_vars)



# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)
# humidity = np.random.normal(0.3, 0.3, 10)
# x2 = get_Gd(when, latitude, longitude, humidity)
# print(x2)

def get_beam_ground(**kwargs):
    # Calculate the direct solar beam at the ground level
    try:
        kwargs['beam_ground'] = np.subtract(kwargs['irradiance_ground'], kwargs['diffused_ground'])    
    except Exception as e:
        print("Error solar get_beam_ground:", e)
    
    return kwargs

### test
# dict_vars = get_beam_ground(**dict_vars)


# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*6))
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)
# humidity = np.random.normal(0.3, 0.3, 10)
# x2 = get_Gb(when, latitude, longitude, humidity)
# print(x2)



def get_ratio_tilted_horizontal(**kwargs):
    # This function calculates the ratio of solar radiation on a tilted surface and a horizontal surface
    try:
        cos_inc = np.cos(np.radians(kwargs['incidence_angle']))
        cos_zen = np.cos(np.radians(kwargs['zenith_angle']))
        
        idx = np.flatnonzero((kwargs['zenith_angle']>=90))
        
        kwargs['ratio_tilted_horizontal'] = np.clip(np.array(np.divide(cos_inc, cos_zen)), a_min=0, a_max=9999)
        kwargs['ratio_tilted_horizontal'][idx] = 0
        
        ###################
        # cos_lat = np.cos(np.radians(kwargs['latitude']))
        # cos_dec = np.cos(np.radians(kwargs['declination']))
        # cos_tilt = np.cos(np.radians(kwargs['tilt']))
        # cos_azim = np.cos(np.radians(kwargs['azimuth']))

        # sin_lat = np.sin(np.radians(kwargs['latitude']))
        # sin_dec = np.sin(np.radians(kwargs['declination']))
        # sin_tilt = np.sin(np.radians(kwargs['tilt']))
        # sin_azim = np.sin(np.radians(kwargs['azimuth']))
        
        # w2 = kwargs['hour_angle']
        # w1 = np.subtract(kwargs['hour_angle'], 0.0001)

        # cos_w1 = np.cos(np.radians(w1))
        # cos_w2 = np.cos(np.radians(w2))
        # sin_w1 = np.sin(np.radians(w1))
        # sin_w2 = np.sin(np.radians(w2))


        # a = (((sin_dec * sin_lat * cos_tilt) - (sin_dec * cos_lat * sin_tilt * cos_azim)) * (np.pi/180)*(w2-w1)) \
        #     + (((cos_dec*cos_lat*cos_tilt)+(cos_dec*sin_lat*sin_tilt*cos_azim)) * (sin_w2 - sin_w1)) \
        #     - ((cos_dec * sin_tilt * sin_azim)*(cos_w2 - cos_w1))



        # b = ((cos_lat*cos_dec)*(sin_w2-sin_w1)) + ((sin_lat + sin_dec) * (np.pi/180)*(w2 - w1))

        # kwargs['ratio_tilted_horizontal'] = np.clip((np.divide(a, b)), a_min=0, a_max=999)

    except Exception as e:
        print("Error solar get_ratio_tilted_horizontal:", e)
    return kwargs

### test
# dict_vars = get_ratio_tilted_horizontal(**dict_vars)



def get_irradiance_isotropic(**kwargs):
    # This function calculates the irradiance on a tilted plane using the isotropic model
    # Isotropic model assumes that the sky opacity is homogeneous
    try:
        partial_beam = (kwargs['beam_ground']*kwargs['ratio_tilted_horizontal'])
        partial_diffused = (kwargs['diffused_ground']*0.5*(1+np.cos(np.radians(kwargs['tilt']))))
        partial_albedo = (kwargs['irradiance_ground']*kwargs['albedo']*0.5*(1-np.cos(np.radians(kwargs['tilt']))))
        kwargs['irradiance_isotropic'] = np.clip((np.add(partial_beam, np.add(partial_diffused, partial_albedo))), a_min=0, a_max=2000)
    except Exception as e:
        print("Error solar get_irradiance_isotropic:", e)
    return kwargs

### test
# dict_vars = get_irradiance_isotropic(**dict_vars)


# ### ------test -----------------------
# when = time.localtime(time.time() - (3600*7))
# print(when)
# latitude = np.random.normal(-32, 1, 10)
# longitude = np.random.normal(118, 1, 10)
# elevation = np.random.normal(30, 1, 10)
# tilt = np.random.normal(30, 3, 10)
# azimuth = np.random.normal(180, 3, 10)
# albedo = np.random.normal(2, 0.1, 10)
# humidity = np.random.normal(0.3, 0.3, 10)
# x2 = get_Gt_isotropic(when, latitude, longitude, elevation, tilt, azimuth, albedo, humidity)
# print(x2)


def get_irradiance_hdkr(**kwargs):
    # This function uses the model of Hay, Davies, Klucher, and Reindl (HDKR)
    # to forecast the available solar radiation for 1 hour interval
    try:
        Ai = np.zeros(kwargs['longitude'].shape)
        f = np.zeros(kwargs['longitude'].shape)
        
        idx = np.flatnonzero((kwargs['outer_beam_horizontal']>0))
        Ai[idx] = np.divide(kwargs['beam_ground'][idx], kwargs['outer_beam_horizontal'][idx])
        f[idx] = np.sqrt(np.clip(np.divide(kwargs['beam_ground'][idx], kwargs['irradiance_ground'][idx]), a_min=0, a_max=9999))


        partial_beam = np.multiply(np.add(kwargs['beam_ground'], np.multiply(kwargs['diffused_ground'], Ai)), kwargs['ratio_tilted_horizontal'])
        partial_diffused1 = np.multiply(kwargs['diffused_ground'], np.subtract(1, Ai))
        partial_diffused2 = np.multiply(0.5, np.add(1, np.cos(np.radians(kwargs['tilt']))))
        partial_diffused3 = np.add(1, np.multiply(f, np.power((np.sin(np.multiply(0.5, np.radians(kwargs['tilt'])))), 3)))
        partial_diffused = np.multiply(partial_diffused1, np.multiply(partial_diffused2, partial_diffused3))
        partial_albedo1 = np.multiply(kwargs['irradiance_ground'], kwargs['albedo'])
        partial_albedo2 = np.multiply(0.5, np.subtract(1, np.cos(np.radians(kwargs['tilt']))))
        partial_albedo = np.multiply(partial_albedo1, partial_albedo2)


        kwargs['irradiance_hdkr'] = np.clip((partial_beam + partial_diffused + partial_albedo), a_min=0, a_max=10000)
    except Exception as e:
        print("Error solar get_irradiance_hdkr:", e)
    return kwargs


### test
# dict_vars = get_irradiance_hdkr(**dict_vars)


def get_irradiance_perez(**kwargs):
    '''
    This function calculates the solar irradiation on a tilted surface
    using the model proposed by Perez et.al. (1990)
    '''
    try:
        cos_lat = np.cos(np.radians(kwargs['latitude']))
        cos_dec = np.cos(np.radians(kwargs['declination']))
        cos_tilt = np.cos(np.radians(kwargs['tilt']))
        cos_azim = np.cos(np.radians(kwargs['azimuth']))
        cos_zen = np.cos(np.radians(kwargs['zenith_angle']))
        cos_inc = np.cos(np.radians(kwargs['incidence_angle']))

        sin_lat = np.sin(np.radians(kwargs['latitude']))
        sin_dec = np.sin(np.radians(kwargs['declination']))
        sin_tilt = np.sin(np.radians(kwargs['tilt']))
        sin_azim = np.sin(np.radians(kwargs['azimuth']))
        
        w2 = kwargs['hour_angle']
        w1 = np.subtract(kwargs['hour_angle'], 0.0001)

        cos_w1 = np.cos(np.radians(w1))
        cos_w2 = np.cos(np.radians(w2))
        sin_w1 = np.sin(np.radians(w1))
        sin_w2 = np.sin(np.radians(w2))

        Id = kwargs['diffused_ground']
        Ibn = kwargs['beam_ground'] / cos_zen
        theta_z = kwargs['zenith_angle']

        ### clearness
        kwargs["e"] = ((((Id + Ibn )/Id) + (5.535*1e-6 * theta_z**3))) / (1 + (5.535*1e-6 * theta_z**3))

        kwargs["f11"] = np.zeros(kwargs["e"].shape)
        kwargs["f12"] = np.zeros(kwargs["e"].shape)
        kwargs["f13"] = np.zeros(kwargs["e"].shape)
        kwargs["f21"] = np.zeros(kwargs["e"].shape)
        kwargs["f22"] = np.zeros(kwargs["e"].shape)
        kwargs["f23"] = np.zeros(kwargs["e"].shape)
        
        idx1 = np.flatnonzero((kwargs["e"]>1.000)&(kwargs["e"]<=1.065))
        idx2 = np.flatnonzero((kwargs["e"]>1.065)&(kwargs["e"]<=1.230))
        idx3 = np.flatnonzero((kwargs["e"]>1.230)&(kwargs["e"]<=1.500))
        idx4 = np.flatnonzero((kwargs["e"]>1.500)&(kwargs["e"]<=1.950))
        idx5 = np.flatnonzero((kwargs["e"]>1.950)&(kwargs["e"]<=2.800))
        idx6 = np.flatnonzero((kwargs["e"]>2.800)&(kwargs["e"]<=4.500))
        idx7 = np.flatnonzero((kwargs["e"]>4.500)&(kwargs["e"]<=6.200))
        idx8 = np.flatnonzero((kwargs["e"]>6.200))

        if np.size(idx1):
            kwargs['f11'][idx1] = -0.008
            kwargs['f12'][idx1] = 0.588
            kwargs['f13'][idx1] = -0.062
            kwargs['f21'][idx1] = -0.060
            kwargs['f22'][idx1] = 0.072
            kwargs['f23'][idx1] = -0.022

        elif np.size(idx2):
            kwargs['f11'][idx2] = 0.130
            kwargs['f12'][idx2] = 0.683
            kwargs['f13'][idx2] = -0.151
            kwargs['f21'][idx2] = -0.019
            kwargs['f22'][idx2] = 0.066
            kwargs['f23'][idx2] = -0.029
            
        elif np.size(idx3):
            kwargs['f11'][idx3] = 0.330
            kwargs['f12'][idx3] = 0.487
            kwargs['f13'][idx3] = -0.221
            kwargs['f21'][idx3] = 0.055
            kwargs['f22'][idx3] = -0.064
            kwargs['f23'][idx3] = -0.026
            
        elif np.size(idx4):
            kwargs['f11'][idx4] = 0.568
            kwargs['f12'][idx4] = 0.187
            kwargs['f13'][idx4] = -0.295
            kwargs['f21'][idx4] = 0.109
            kwargs['f22'][idx4] = -0.152
            kwargs['f23'][idx4] = 0.014
            
        elif np.size(idx5):
            kwargs['f11'][idx5] = 0.873
            kwargs['f12'][idx5] = -0.392
            kwargs['f13'][idx5] = -0.362
            kwargs['f21'][idx5] = 0.226
            kwargs['f22'][idx5] = -0.462
            kwargs['f23'][idx5] = 0.001
            
        elif np.size(idx6):
            kwargs['f11'][idx6] = 1.132
            kwargs['f12'][idx6] = -1.237
            kwargs['f13'][idx6] = -0.412
            kwargs['f21'][idx6] = 0.288
            kwargs['f22'][idx6] = -0.823
            kwargs['f23'][idx6] = 0.056
            
        elif np.size(idx7):
            kwargs['f11'][idx7] = 1.060
            kwargs['f12'][idx7] = -1.600
            kwargs['f13'][idx7] = -0.359
            kwargs['f21'][idx7] = 0.264
            kwargs['f22'][idx7] = -1.127
            kwargs['f23'][idx7] = 0.131
            
        elif np.size(idx8):
            kwargs['f11'][idx8] = 0.678
            kwargs['f12'][idx8] = -0.327
            kwargs['f13'][idx8] = -0.250
            kwargs['f21'][idx8] = 0.156
            kwargs['f22'][idx8] = -1.377
            kwargs['f23'][idx8] = 0.251
            

        a = np.clip(cos_inc, a_min=0, a_max=99)
        b = np.clip(cos_zen, a_min=np.cos(np.radians(85)), a_max=99)
        delta = kwargs['airmass'] * (kwargs['diffused_ground'] / kwargs['outer_beam_normal'])  # brightness

        F1 = (kwargs["f11"] + (kwargs["f12"]*delta) + (np.radians(theta_z) * kwargs["f13"]))
        F2 = kwargs["f21"] + (kwargs["f22"]*delta) + ((np.pi/180)*(theta_z) * kwargs["f23"])
        F1 = np.clip(F1, a_min=0, a_max=1)
        F2 = np.clip(F2, a_min=0, a_max=1)
        partial_beam = (kwargs['beam_ground'] * kwargs['ratio_tilted_horizontal'])
        diffused_isotropic = (kwargs['diffused_ground']* (1 - F1)) * (0.5*(1 + cos_tilt))
        diffused_circumsolar = (kwargs['diffused_ground'] * F1 * (a/b))
        diffused_horizon = (kwargs['diffused_ground'] * F2 * sin_tilt)
        partial_albedo = (kwargs['irradiance_ground'] * kwargs['albedo']) * (0.5*np.subtract(1,cos_tilt))

        n = 0
        partial_beam = np.clip(partial_beam, a_min=0, a_max=999)
        diffused_isotropic = np.clip(diffused_isotropic, a_min=0, a_max=999)
        diffused_circumsolar =  np.clip(diffused_circumsolar, a_min=0, a_max=999)
        diffused_horizon = np.clip(diffused_horizon, a_min=0, a_max=999)
        partial_albedo = np.clip(partial_albedo, a_min=0, a_max=999) 
        
        kwargs['irradiance_perez'] = partial_beam + diffused_isotropic + diffused_circumsolar + diffused_horizon + partial_albedo
        # print(kwargs['ratio_tilted_horizontal'], (a/b), kwargs['e'])
    except Exception as e:
        print("Error solar get_irradiance_perez:", e)
    return kwargs


def clean_visibility(visibility):
    # This function cleans the visibility data
    # From the Koshmeider equation: visibility = 3.912/ extinction coefficient
    # At sea level, Rayleigh's atmosphere (the cleanest possible) has an extinction coefficient of 13.2x10^-6 m^-1 at 520nm wavelength
    # so, visibility limit is 296 km.
    # Parameter: visibility = data from weather station in meters
    try:
        clean = np.clip(visibility,0,296000)
    except Exception as e:
        print("Error solar clean_visibility:", e)
    return clean


def get_irradiance(**kwargs):
    # kwargs.update(
    #         {
    #             "e1":{"f11":-0.008,"f12":0.588,"f13":-0.062,"f21":-0.060,"f22":0.072,"f23":-0.022},
    #             "e2":{"f11":0.130, "f12":0.683,"f13":-0.151,"f21":-0.019,"f22":0.066,"f23":-0.029},
    #             "e3":{"f11":0.330, "f12":0.487,"f13":-0.221,"f21":0.055,"f22":-0.064,"f23":-0.026},
    #             "e4":{"f11":0.568, "f12":0.187,"f13":-0.295,"f21":0.109,"f22":-0.152,"f23":0.014},
    #             "e5":{"f11":0.873, "f12":-0.392,"f13":-0.362,"f21":0.226,"f22":-0.462,"f23":0.001},
    #             "e6":{"f11":1.132, "f12":-1.237,"f13":-0.412,"f21":0.288,"f22":-0.823,"f23":0.056},
    #             "e7":{"f11":1.060, "f12":-1.600,"f13":-0.359,"f21":0.264,"f22":-1.127,"f23":0.131},
    #             "e8":{"f11":0.678, "f12":-0.327,"f13":-0.250,"f21":0.156,"f22":-1.377,"f23":0.251},
    #         }
    #     )

    dict_vars = get_yday(**kwargs)
    dict_vars = get_climate_type(**dict_vars)
    dict_vars = get_solar_time(**dict_vars)
    dict_vars = get_hour_angle(**dict_vars)
    dict_vars = get_declination(**dict_vars)
    dict_vars = get_sunset_hour_angle(**dict_vars)
    dict_vars = get_sunrise_hour_angle(**dict_vars)
    dict_vars = get_zenith_angle(**dict_vars)
    dict_vars = get_solar_altitude(**dict_vars)
    dict_vars = get_solar_azimuth(**dict_vars)
    dict_vars = get_incidence_angle(**dict_vars)
    dict_vars = get_daylight_hours(**dict_vars)
    dict_vars = get_profile_angle(**dict_vars)
    dict_vars = get_sunset_hour(**dict_vars)
    dict_vars = get_sunrise_hour(**dict_vars)
    dict_vars = get_airmass(**dict_vars)
    dict_vars = get_one_day_solar(**dict_vars)
    dict_vars = get_outer_beam_normal(**dict_vars)
    dict_vars = get_outer_beam_horizontal(**dict_vars)
    dict_vars = get_clearsky_beam_horizontal(**dict_vars)
    dict_vars = get_clearsky_diffused_horizontal(**dict_vars)
    dict_vars = get_clearsky_horizontal(**dict_vars)
    dict_vars = get_clearness_index(**dict_vars)
    dict_vars = get_solar_ground(**dict_vars)
    dict_vars = get_diffused_ground(**dict_vars)
    dict_vars = get_beam_ground(**dict_vars)
    dict_vars = get_ratio_tilted_horizontal(**dict_vars)
    dict_vars = get_irradiance_isotropic(**dict_vars)  #[W/m^2]
    dict_vars = get_irradiance_hdkr(**dict_vars) #[W/m^2]
    # dict_vars = get_irradiance_perez(**dict_vars) #[W/m^2]
    
    return dict_vars['irradiance_hdkr']

#################### Test call ####################################################

def main(dict_vars):
    irradiance = get_irradiance(**dict_vars)


    print(irradiance)
    return irradiance

if __name__ == '__main__':
    data = []
    dict_vars = {}
    dt_range = pd.date_range('2018-07-16 06:00:00',
                freq='60S', periods=int(60*15*1), tz='Pacific/Auckland')

    # dict_vars.update(
    #         {
    #             'latitude': np.random.normal(-36.86667, 0.0001, 3),
    #             'longitude': np.random.normal(174.76667, 0.0001, 3),
    #             'elevation': np.random.normal(30, 1, 3),
    #             'tilt': np.random.normal(30, 10, 3),
    #             'azimuth': np.random.normal(-90, 90, 3),
    #             'albedo': np.random.normal(0.2, 0.1, 3),
    #             'humidity': np.random.normal(0.5, 0.3, 3),

    #         }
    #     )

    for dt in dt_range:
        dict_vars.update({'unixtime':dt.timestamp(), 'timezone':'Pacific/Auckland'})
        dict_vars.update(
            {
                'latitude': np.array([-36.86656223, -36.86656223, -36.86660351]), 
                'longitude': np.array([174.76659403, 174.76659403, 174.76667513]), 
                'elevation': np.array([29.92616073, 29.92616073, 29.41078759]), 
                'tilt': np.array([0, 0, 33.65287833]), 
                'azimuth': np.array([  180.27189771,  -99.31783374, -180.21836098]), 
                'albedo': np.array([0.19355514, 0.19355514, 0.16194601]), 
                'humidity': np.array([0.2749629, 0.2749629, 0.36294318])
            }
        )
        data.append(main(dict_vars))

    # data = np.array(data)
    # df_data = pd.DataFrame(data)
    # df_data.index = dt_range
    # # print(df_data)
    # df_data.plot()
    # plt.show()

# solar pv efficiencies: min, max, avg
# source: https://news.energysage.com/what-are-the-most-efficient-solar-panels-on-the-market/
'''

SunPower    16.00%  22.20%  19.96%
Panasonic   18.50%  20.30%  19.41%
Solaria 18.70%  19.90%  19.25%
Solartech Universal 17.80%  20.20%  19.00%
LG  16.80%  21.10%  18.78%
CertainTeed Solar   17.10%  19.40%  18.34%
LONGi Solar 17.40%  18.70%  18.02%
Itek Energy 16.49%  18.94%  17.98%
Winaico 16.50%  18.90%  17.85%
Flex    17.43%  18.04%  17.74%
Upsolar 16.20%  19.40%  17.73%
Silevo  16.90%  18.50%  17.70%
Hanwha Q CELLS  14.70%  19.60%  17.32%
Heliene 15.60%  19.30%  17.31%
Recom Solar 16.00%  19.00%  17.31%
Renogy Solar    15.30%  18.50%  17.30%
BenQ Solar (AUO)    15.50%  18.30%  17.19%
Mission Solar   15.98%  18.36%  17.15%
Suniva Inc  16.66%  17.65%  17.14%
Talesun 16.10%  18.20%  17.14%
Silfab  15.30%  20.00%  17.12%
JinkoSolar  15.57%  18.57%  16.96%
Peimar Group    15.40%  18.40%  16.94%
Phono Solar 15.36%  18.55%  16.94%
Canadian Solar  15.88%  18.33%  16.93%
JA Solar    15.50%  18.35%  16.83%
Grape Solar 16.21%  17.64%  16.75%
SolarWorld  14.91%  17.59%  16.66%
Mitsubishi Electric 16.30%  16.90%  16.60%
Boviet Solar    15.40%  17.50%  16.56%
Seraphim    15.67%  17.52%  16.55%
ET Solar    15.37%  17.52%  16.51%
Hansol  14.97%  18.05%  16.49%
Neo Solar Power 16.00%  17.00%  16.48%
Axitec  15.37%  17.90%  16.47%
REC Solar   14.50%  19.80%  16.47%
S-Energy    14.62%  18.70%  16.45%
Trina Solar Energy  15.00%  18.60%  16.35%
CentroSolar 15.30%  17.80%  16.21%
SunEdison   15.50%  16.80%  16.12%
Hyundai 14.20%  18.40%  16.03%
Amerisolar  14.75%  17.01%  15.97%
ReneSola    14.90%  16.90%  15.91%
China Sunergy   14.98%  16.53%  15.78%
Hanwha SolarOne 14.70%  16.20%  15.45%
Kyocera 14.75%  16.11%  15.42%
Green Brilliance    14.24%  15.58%  15.03%
Stion   12.40%  14.00%  13.20%

'''