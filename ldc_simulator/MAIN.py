#############################################################
# Codes for the main file to simulate Aggregation of Flexible Loads
# by: Ryan Tulabing
# University of Auckland, 2017
#############################################################

from AGGREGATOR import *


################ MAIN FUNCTION #################################################

finished_cases = ['/basic_cd_cw_k128_auto', '/basic_cd_eh_k128_auto', '/basic_cd_fg_k128_auto', 
                    '/basic_cd_hp_k128_auto', '/basic_cd_k128_auto', '/basic_cd_wh_k128_auto', '/basic_cw_eh_k128_auto', 
                    '/basic_cw_fg_k128_auto', '/basic_cw_hp_k128_auto', '/basic_cw_k128_auto', '/basic_cw_wh_k128_auto', 
                    '/basic_eh_fg_k128_auto', '/basic_eh_hp_k128_auto', '/basic_eh_k128_auto', '/basic_eh_wh_k128_auto', 
                    '/basic_fg_hp_k128_auto', '/basic_fg_k128_auto', '/basic_fg_wh_k128_auto', '/basic_hp_k128_auto', 
                    '/basic_hp_wh_k128_auto', '/basic_wh_k128_auto']


if __name__ == '__main__':
    parser = OptionParser(version=' ')
    parser.add_option('-i', '--index', dest='idx', default=0, help='starting index')
    parser.add_option('-n', '--number', dest='n', default=5, help='number of units')
    parser.add_option('-s', '--simulate', dest='s', default=0, help='simulation mode')
    parser.add_option('-c', '--case', dest='c', default=0, help='simulation case')
    parser.add_option('-e', '--season', dest='e', default=0, help='simulation season')
    parser.add_option('-d', '--days', dest='d', default=0, help='number of days to simulate')
    parser.add_option('-t', '--timestep', dest='t', default=1, help='timestep')
    parser.add_option('-k', '--network', dest='k', default=0, help='network to use')
    parser.add_option('-a', '--adoption', dest='a', default=0, help='ldc adoption rate')
    parser.add_option('--algorithm', dest='algorithm', default='basic_ldc', help='algorithm used')
    parser.add_option('--distribution', dest='distribution', default='per_house', help='distribution of ldc-enabled devices')
    parser.add_option('--ranking', dest='ranking', default='static', help='prioritization of flexible devices')
    parser.add_option('--target', dest='target', default='auto', help='target loading percent')
    parser.add_option('--delay', dest='delay', default=0, help='delay of signal reaching the dongles')
    parser.add_option('--ki', dest='ki', default='ki', help='integral loop constant')
    # parser.add_option('--avg', dest='avg', default=86400, help='seconds for rolling average, default is 1 day')
    parser.add_option('--resolution', dest='resolution', default=-1, help='resolution of ldc signal sensor')
    parser.add_option('--enabled', dest='enabled', default='all', help='ldc-enabled appliance')
    parser.add_option('--schedule', dest='schedule', default=0, help='demand response event schedule')
    parser.add_option('--tcl_control', dest='tcl_control', default='mixed', help='control method of TCLs')
    parser.add_option('--folder', dest='folder', default='/home/pi/studies/results/assorted', help='folder name')
    parser.add_option('--report', dest='report', default=0, help='show data during tests and troubleshooting')
    parser.add_option('--flex', dest='flex', default=100, help='weight for flexibility-based prioritization')
    parser.add_option('--study', dest='study', default='None', help='Simulation study')
    parser.add_option('--ev', dest='ev', default='None', help='Adoption of ev')
    parser.add_option('--battery', dest='battery', default='None', help='Adoption of battery')
    parser.add_option('--solar', dest='solar', default='None', help='Adoption of solar')
    parser.add_option('--wind', dest='wind', default='None', help='Adoption of wind')

    options, args = parser.parse_args(sys.argv[1:])
    report = int(options.report)
    simulation = int(options.s)
    dict_cases = {0:None, 
                1:'no_ldc',
                2:'ripple_control',
                3:'loading_10', 
                4:'loading_20', 
                5:'loading_30', 
                6:'loading_40',  
                7:'loading_50', 
                8:'adoption_10',
                9:'adoption_20',
                10:'adoption_30',
                11:'adoption_40',
                12:'adoption_50',
                13:'adoption_60',
                14:'adoption_70',
                15:'adoption_80',
                16:'adoption_90',
                17:'adoption_100',
                18:'basic_ldc_waterheater',
                19:'basic_ldc_dynamic',  
                20:'advanced_ldc',
                21:'loading_avg1h',
                22:'resolution_1hz',
                23:'resolution_10hz',
                24:'resolution_1uhz',
                25:'loading_auto',

                31:'ideal_direct_k32_tou_step100ms',
                32:'ideal_direct_k32_tou_step1s',
                33:'ideal_direct_k32_tou_step5s',
                34:'ldc_direct_k32_t50_step1s_halfdb', # duration is 1.75 day
                35:'ldc_setpoint_k32_t50_step1s_halfdb', # duration is 1.75 day
                
                101:'ramp_direct_k16_t100_d0s',
                102:'ramp_direct_k32_t100_d0s',
                103:'ramp_direct_k64_t100_d0s',
                104:'ramp_direct_k128_t100_d0s',
                105:'ramp_direct_k256_t100_d0s',
                106:'ramp_direct_k512_t100_d0s',
                107:'ramp_direct_k1024_t100_d0s',
                108:'ramp_direct_k2048_t100_d0s',
                109:'ramp_direct_k4096_t100_d0s',
                110:'ramp_direct_k8192_t100_d0s',
                
                111:'ramp_direct_k16_t100_d1s',
                112:'ramp_direct_k32_t100_d1s',
                113:'ramp_direct_k64_t100_d1s',
                114:'ramp_direct_k128_t100_d1s',
                115:'ramp_direct_k256_t100_d1s',
                116:'ramp_direct_k512_t100_d1s',
                117:'ramp_direct_k1024_t100_d1s',
                118:'ramp_direct_k2048_t100_d1s',
                119:'ramp_direct_k4096_t100_d1s',
                110:'ramp_direct_k8192_t100_d1s',
                
                121:'ideal_direct_k16_tou',
                122:'ideal_direct_k32_tou',
                123:'ideal_direct_k64_tou',
                124:'ideal_direct_k128_tou',
                125:'ideal_direct_k256_tou',
                126:'ideal_direct_k512_tou',
                127:'ideal_direct_k1024_tou',
                128:'ideal_direct_k2048_tou',
                129:'ideal_direct_k4096_tou',
                130:'ideal_direct_k8192_tou',
                

                131:'ideal_setpoint_k16_tou',
                132:'ideal_setpoint_k32_tou',
                133:'ideal_setpoint_k64_tou',
                134:'ideal_setpoint_k128_tou',
                135:'ideal_setpoint_k256_tou',
                136:'ideal_setpoint_k512_tou',
                137:'ideal_setpoint_k1024_tou',
                138:'ideal_setpoint_k2048_tou',
                139:'ideal_setpoint_k4096_tou',
                140:'ideal_setpoint_k8192_tou',
                

                141:'ideal_setpoint2_k16_tou',
                142:'ideal_setpoint2_k32_tou',
                143:'ideal_setpoint2_k64_tou',
                144:'ideal_setpoint2_k128_tou',
                145:'ideal_setpoint2_k256_tou',
                146:'ideal_setpoint2_k512_tou',
                147:'ideal_setpoint2_k1024_tou',
                148:'ideal_setpoint2_k4096_tou',
                149:'ideal_setpoint2_k8192_tou',
                
                
                200:'ideal_basic_direct_a0.1_t33',
                201:'ideal_basic_setpoint_a0.1_t33',
                202:'ideal_basic_mixed_a0.1_t33',
                203:'basic_direct_perhouse_a0.1_t33',
                204:'basic_direct_perdevice_a0.1_t33',

                211:'ideal_mixed2_k10_tou',
                212:'ideal_mixed2_k20_tou',
                213:'ideal_mixed2_k30_tou',
                214:'ideal_mixed2_k40_tou',
                215:'ideal_mixed2_k50_tou',
                216:'ideal_mixed2_k60_tou',
                217:'ideal_mixed2_k70_tou',
                218:'ideal_mixed2_k80_tou',
                219:'ideal_mixed2_k90_tou',
                220:'ideal_mixed2_k100_tou',

                223:'basic_mixed_k64_t50_d500ms',
                224:'basic_mixed_k256_t50_d500ms',
                225:'basic_mixed_k512_t50_d500ms',
                226:'basic_mixed_k1024_t50_d500ms',
                227:'basic_mixed_k2048_t50_d500ms',

                231:'basic_mixed_k512_t50_d100ms',
                232:'basic_mixed_k512_t50_d1s',
                233:'basic_mixed_k512_t50_d2s',
                
                241:'no_ldc',
                242:'ripple_control',
                243:'basic_all_k256_t50_d1s',
                244:'basic_wh_k256_t50_d1s',
                245:'advanced_all_k256_t50_d1s',
                246:'advanced_wh_k256_t50_d1s',


                301:'basic_all_k128_auto_d1s',
                302:'basic_wh_k128_auto_d1s',

                271:'advanced_all_k256_auto_d1s_t100ms',
                272:'advanced_all_k256_auto_d1s_t200ms',
                273:'advanced_all_k256_auto_d1s_t300ms',
                274:'advanced_all_k256_auto_d1s_t500ms',
                275:'advanced_all_k256_auto_d1s_t800ms',
                276:'advanced_all_k256_auto_d1s_t1000ms',
                277:'advanced_all_k256_auto_d1s_t1300ms',

                279:'basic_all_k128_auto_d1s_step1s_f0',
                280:'advanced_all_k128_auto_d1s_step1s_f0',
                281:'advanced_all_k128_auto_d1s_step1s_f10',
                283:'advanced_all_k128_auto_d1s_step1s_f30',
                285:'advanced_all_k128_auto_d1s_step1s_f50',
                287:'advanced_all_k128_auto_d1s_step1s_f70',
                289:'advanced_all_k128_auto_d1s_step1s_f90',
                290:'advanced_all_k32_t50_f100',
                291:'advanced_all_k32_auto_f100',

                292:'advanced_all_a0.1_t33_f100',
                293:'advanced_all_a0.2_t33_f100',
                294:'advanced_all_a0.5_t33_f100',
                295:'advanced_all_a2.0_t33_f100',
                296:'advanced_all_a5.0_t33_f100',
                297:'advanced_all_a10.0_t33_f100',
                
                


                400: 'ldc_0_ev_0',
                401: 'ldc_0_ev_10',
                402: 'ldc_0_ev_20',
                403: 'ldc_0_ev_30',
                404: 'ldc_0_ev_40',
                405: 'ldc_0_ev_50',
                406: 'ldc_0_ev_60',
                407: 'ldc_0_ev_70',
                408: 'ldc_0_ev_80',
                409: 'ldc_0_ev_90',
                410: 'ldc_0_ev_100',

                501: 'ldc_100_ev_10',
                502: 'ldc_100_ev_20',
                503: 'ldc_100_ev_30',
                504: 'ldc_100_ev_40',
                505: 'ldc_100_ev_50',
                506: 'ldc_100_ev_60',
                507: 'ldc_100_ev_70',
                508: 'ldc_100_ev_80',
                509: 'ldc_100_ev_90',
                610: 'ldc_100_ev_100',

                701: 'ldc_0_solar_10',

                }

    dict_schedule = {0:'always', 
                1:'fixedtime', 
                3:'peaktime', 
                4:'emergency'}
    dict_season = {0:None, 
                1:'winter', 
                2:'summer', 
                3:'spring', 
                4:'autumn'}
    dict_season_week = {'summer':3, 
                'autumn':16, 
                'winter': 29, 
                'spring':42}
    dict_network = {0:'lv_1', 
                1:'lv_5', 
                2:'lv_60', 
                3:'dickert_lv_long', 
                4:'ieee_european_lv' }
    dict_enabled = {'wh':'waterheater', 
                'hp':'heatpump', 
                'ht':'heater', 
                'fg':'fridge', 
                'fz':'freezer', 
                'cw':'clotheswasher', 
                'cd':'clothesdryer', 
                'dw':'dishwasher'}
    dict_algorithm = {'0':'no_ldc', 
                '1':'basic_ldc', 
                '2':'advanced_ldc', 
                '3':'ripple_control'}

    
    
    if simulation==1:
        case = dict_cases[int(options.c)]
        season = dict_season[int(options.e)]
        ndays = float(options.d)
        step_size = float(options.t)
        network = dict_network[int(options.k)]
        device_ip = 200
        start_idx = options.idx
        savepath = options.folder
        target = options.target
        # avg = float(options.avg)
        resolution = int(options.resolution)
        enabled = options.enabled
        algorithm = options.algorithm
        distribution = options.distribution
        ranking = options.ranking
        tcl_control = options.tcl_control
        ki = float(options.ki)
        delay = float(options.delay)
        flex_percent = float(options.flex)
        study = options.study
        ### define ratio of 
        app_per_house = dict(house=1, baseload=1, heatpump=0.61, heater=1.31, waterheater=0.8,
                fridge=1.31, freezer=0.5, clotheswasher=1.08, clothesdryer=0.7816,
                dishwasher=0.6931, ev=0.3, storage=0.3, solar=0.3, wind=0.3)



        if network=='dickert_lv_long':
            n_units = 60
            savepath = '/home/pi/studies/results/dickert_lv_long'
        elif network=='ieee_european_lv':
            n_units = 55
            savepath = '/home/pi/studies/results/ieee_european_lv'
        elif network=='lv_1':
            n_units = 1
            for k in app_per_house.keys(): app_per_house[k] = 1
            savepath = '/home/pi/studies/results/lv_1'
        elif network=='lv_5':
            n_units = 5
            for k in app_per_house.keys(): app_per_house[k] = 1
            savepath = '/home/pi/studies/results/lv_5'
        elif network=='lv_60':
            n_units = 60
            savepath = '/home/pi/studies/results/lv_60'
        else:
            n_units = int(options.n)

        casefolder = savepath.split('/')[-1]
        os.makedirs(savepath, exist_ok=True)  # create the folder to store results
            

        latitude = '-36.866590076725494'
        longitude = '174.77534779638677'

        dt = pd.date_range(start='2020-1-1 00:00:00', end='2021-1-1 00:00').tz_localize('Pacific/Auckland')
        dt_start = [a for a in dt if a.week==dict_season_week[season]][4]  # week in the middle of season, day of week
        start = dt_start.timestamp()
        devices_to_simulate = ['house', 'baseload', 
            'heatpump', 'heater', 'waterheater', 'fridge', 'freezer',   # thermostat controlled
            'clotheswasher', 'clothesdryer', 'dishwasher',              # non-thermostat controlled
            # 'ev', 
            # 'storage',                                          # battery-based
            # 'solar', 
            # 'wind'                                           # local generation
            ]

        if study=='tcl_control':
            n_ldc = float(options.a)
            dict_devices = {k:{'n_units':int(n_units*app_per_house[k]), 'n_ldc':0} for k in devices_to_simulate}
            dict_devices['heatpump']['n_ldc'] = int(n_units*n_ldc*app_per_house['heatpump'])
            dict_devices['fridge']['n_ldc'] = int(n_units*n_ldc*app_per_house['fridge'])
            dict_devices['freezer']['n_ldc'] = int(n_units*n_ldc*app_per_house['freezer'])
            dict_devices['heater']['n_ldc'] = int(n_units*n_ldc*app_per_house['heater'])
            dict_devices['waterheater']['n_ldc'] = int(n_units*n_ldc*app_per_house['waterheater'])
            print('Running setup...')
            for k, v in dict_devices.items(): print(k, v)
            print(f'timestamp:{start}')
            print(f'latitude:{latitude}')
            print(f'longitude:{longitude}')
            print(f'profile index:{start_idx}')
            print(f'device_ip:{device_ip}')
            print(f'case:{case}')
            print(f'season:{season}')  
            local_ip = get_local_ip()          
            A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, 
                idx=start_idx, local_ip=local_ip, device_ip=device_ip, step_size=step_size, simulation=simulation, 
                endstamp=start+int(ndays*3600*24)-1, case=case, network=network, casefolder=casefolder, 
                algorithm=algorithm, target=target, distribution=distribution, ranking=ranking, 
                resolution=resolution, ki=ki, tcl_control=tcl_control, delay=delay, report=report, 
                flex_percent=flex_percent, summary=True)

        elif study=='DER':
            app_per_house = dict(house=1, baseload=1, heatpump=0.61, heater=1.31, waterheater=0.8,
                fridge=1.31, freezer=0.5, clotheswasher=1.08, clothesdryer=0.7816, dishwasher=0.6931, 
                ev=float(options.ev), storage=float(options.battery), solar=float(options.solar), wind=float(options.wind))

            devices_to_simulate = [x for x in app_per_house.keys() if app_per_house[x]>0]
            ldc_devices = [x for x in devices_to_simulate if x not in ['house', 'baseload', 'solar', 'wind']]

            n_ldc = float(options.a)
            dict_devices = {k:{'n_units':int(n_units*app_per_house[k]), 'n_ldc': (k in ldc_devices)*int(n_units*n_ldc*app_per_house[k])} for k in devices_to_simulate}

            # dict_devices['heatpump']['n_ldc'] = int(n_units*n_ldc*app_per_house['heatpump'])
            # dict_devices['fridge']['n_ldc'] = int(n_units*n_ldc*app_per_house['fridge'])
            # dict_devices['freezer']['n_ldc'] = int(n_units*n_ldc*app_per_house['freezer'])
            # dict_devices['heater']['n_ldc'] = int(n_units*n_ldc*app_per_house['heater'])
            # dict_devices['waterheater']['n_ldc'] = int(n_units*n_ldc*app_per_house['waterheater'])
            # dict_devices['ev']['n_ldc'] = int(n_units*n_ldc*app_per_house['ev'])

            print('Running setup...')
            for k, v in dict_devices.items(): 
                print(k, v)
            print(f'timestamp:{start}')
            print(f'latitude:{latitude}')
            print(f'longitude:{longitude}')
            print(f'profile index:{start_idx}')
            print(f'device_ip:{device_ip}')
            print(f'case:{case}')
            print(f'season:{season}')  
            local_ip = get_local_ip()          
            A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, 
                idx=start_idx, local_ip=local_ip, device_ip=device_ip, step_size=step_size, simulation=simulation, 
                endstamp=start+int(ndays*3600*24)-1, case=case, network=network, casefolder=casefolder, 
                algorithm=algorithm, target=target, distribution=distribution, ranking=ranking, 
                resolution=resolution, ki=ki, tcl_control=tcl_control, delay=delay, report=report, 
                flex_percent=flex_percent, summary=True)

        
        elif study=='hierarchy':
            ldc_loads = {
                "wh":["waterheater"], 
                "hp":["heatpump"], 
                "eh":["heater"],
                # "ev":["ev"], 
                # "es":["storage"],
                "fg":["fridge", "freezer"],
                "cw":["clotheswasher", "dishwasher"], 
                "cd":["clothesdryer"], 
                } 

            load_combinations = {}
            # simulate cases for all and combinations of 4
            for i in range(0, len(ldc_loads)+1):
                comb = itertools.combinations(ldc_loads, i)
                for c in list(comb):
                    key = "_".join(np.sort(np.unique(c)))
                    if len(c)==0:
                        load_combinations.update({'none': []})
                    else:
                        loads = []
                        [loads.extend(ldc_loads[k]) for k in c]
                        load_combinations.update({key: loads})

            for key in load_combinations.keys():
                print(key)


            for key, list_loads in load_combinations.items():
                print(list_loads)
                n_ldc = float(options.a)
                dict_devices = {k:{'n_units':int(n_units*app_per_house[k]), 'n_ldc':0} for k in devices_to_simulate}
                for k in list_loads:
                    dict_devices[k]['n_ldc'] = int(n_units*n_ldc*app_per_house[k])
                list_case = case.split('_')
                list_case[1] = key
                newcase = '_'.join(list_case)

                if os.path.exists(f'/home/pi/studies/results/{casefolder}/{newcase}'): 
                    continue
                else:
                    print('Running setup...')
                    for k, v in dict_devices.items(): print(k, v)
                    print(f'timestamp:{start}')
                    print(f'latitude:{latitude}')
                    print(f'longitude:{longitude}')
                    print(f'profile index:{start_idx}')
                    print(f'device_ip:{device_ip}')
                    print(f'case:{newcase}')
                    print(f'season:{season}')  
                    local_ip = get_local_ip()          
                    A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, 
                        idx=start_idx, local_ip=local_ip, device_ip=device_ip, step_size=step_size, simulation=simulation, 
                        endstamp=start+int(ndays*3600*24)-1, case=newcase, network=network, casefolder=casefolder, 
                        algorithm=algorithm, target=target, distribution=distribution, ranking=ranking, 
                        resolution=resolution, ki=ki, tcl_control=tcl_control, delay=delay, report=report, 
                        flex_percent=flex_percent, summary=True)
       
        else:
            n_ldc = float(options.a)
            if case in ['no_ldc']:
                dict_devices = {k:{'n_units':int(n_units*app_per_house[k]), 'n_ldc':0} for k in devices_to_simulate}
            elif (case in ['basic_ldc_waterheater', 'ripple_control']) or ('wh' in case.split('_')):
                dict_devices = {k:{'n_units':int(n_units*app_per_house[k]), 'n_ldc':0} for k in devices_to_simulate}
                dict_devices['waterheater']['n_ldc'] = int(n_units*n_ldc*app_per_house['waterheater'])
            else:
                dict_devices = {k:{'n_units':int(n_units*app_per_house[k]), 'n_ldc':int(n_units*n_ldc*app_per_house[k])} for k in devices_to_simulate}
                
                
            print('Running setup...')
            for k, v in dict_devices.items(): print(k, v)
            print(f'timestamp:{start}')
            print(f'latitude:{latitude}')
            print(f'longitude:{longitude}')
            print(f'profile index:{start_idx}')
            print(f'device_ip:{device_ip}')
            print(f'case:{case}')
            print(f'season:{season}')  
            local_ip = get_local_ip()          
            A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, 
                idx=start_idx, local_ip=local_ip, device_ip=device_ip, step_size=step_size, simulation=simulation, 
                endstamp=start+int(ndays*3600*24)-1, case=case, network=network, casefolder=casefolder, 
                algorithm=algorithm, target=target, distribution=distribution, ranking=ranking, 
                resolution=resolution, ki=ki, tcl_control=tcl_control, delay=delay, report=report, 
                flex_percent=flex_percent, summary=True)


    else:
        dict_config = read_json('/home/pi/ldc_project/config_self.json')
        dict_cmd = read_json('/home/pi/ldc_project/ldc_simulator/dict_cmd.txt')
        algorithm = dict_cmd['algorithm']
        distribution = dict_cmd["distribution"]
        ranking = dict_cmd["ranking"]
        local_ip = get_local_ip()
        start_idx = (int(list(dict_config["group"])[1]) - 1)%5
        device_ip = int(dict_config["id"].split('_')[1])
        n_ldc = 1.0
        n_units = 1
        target = 'auto'
        
        latitude = '-36.866590076725494'
        longitude = '174.77534779638677'
        start = time.time()
        
        # define the number of devices to run
        if device_ip==100:
            dict_devices = {
            'house':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            'baseload':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            'heatpump':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            # 'heater':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},  # no heater in Ardmore to avoid adding cooling load to heatpumps
            'fridge':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            'freezer':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},            
            'clotheswasher':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            'clothesdryer':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            'dishwasher':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            }
        
        # elif device_ip==108:
        #     dict_devices = {
        #     'house':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
        #     'ev':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc), 'v2g':int(n_units)},
        #     }

        # elif device_ip==111:
        #     dict_devices = {
        #     'house':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
        #     'heatpump':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
        #     }
        elif device_ip==112:
            dict_devices = {
            'house':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            'waterheater':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)},
            }
        else:
            dict_devices = {'house':{'n_units':int(n_units), 'n_ldc': int(n_units*n_ldc)}}
            
        print('Running setup...')
        for k, v in dict_devices.items():
            print(k, v)
        print(f'command:{dict_cmd}')
        print(f'timestamp:{start}')
        print(f'latitude:{latitude}')
        print(f'longitude:{longitude}')
        print(f'profile index:{start_idx}')
        print(f'device_ip:{device_ip}')
        # A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, 
        #     idx=start_idx, device_ip=device_ip, step_size=None, simulation=simulation, 
        #     endstamp=None, case='emulation', target=target, algorithm=algorithm, 
        #     distribution=distribution, ranking=ranking)

        A = Aggregator(dict_devices, timestamp=start, latitude=latitude, longitude=longitude, 
            idx=start_idx, local_ip=local_ip, device_ip=device_ip, step_size=None, simulation=simulation, 
            endstamp=None, case='emulation', network='na', casefolder='na', 
            algorithm=algorithm, target=target, distribution=distribution, ranking=ranking, 
            resolution=0, ki=30, tcl_control='mixed', delay=0, report=report)

          


#---- COMMON HOUSE LOAD DEMAND ---
'''
Load                           Minimum         Maximum     Standby     References
100W light bulb (Incandescent)  100W            100W        0W          [1]
25" colour TV                   150W            150W        N/A 
3" belt sander                  1000W           1000W       N/A 
60W light bulb (Incandescent)   60W             60W         0W          [1]
9" disc sander                  1200W           1200W       N/A 
Ceiling Fan                     25W             75W         0W  
Clock radio                     1W              2W          N/A 
Clothes Dryer                   1000W           4000W       N/A 
Coffee Maker                    800W            1400W       N/A 
Cordless Drill Charger          70W             150W        N/A 
Desktop Computer                100W            450W        N/A         [1]
Dishwasher                      1200W           1500W       N/A 
Electric Blanket                200W            200W        N/A 
Electric Heater Fan             2000W           3000W       N/A 
Electric Kettle                 1200W           3000W       0W  
Electric Mower                  1500W           1500W       N/A 
Electric Shaver                 15W             20W         N/A 
Food Blender                    300W            400W        N/A 
Fridge / Freezer                150W            400W        N/A 
Game Console                    120W            200W        N/A         [1]
Hair Blow dryer                 1800W           2500W       N/A 
Home Air Conditioner            1000W           4000W       N/A 
Home Internet Router            5W              15W         N/A 
Hot Water Immersion Heater      3000W           3000W       N/A 
Inkjet Printer                  20W             30W         N/A 
Inverter Air conditioner        1300W           1800W       N/A 
Iron                            1000W           1000W       N/A 
Laptop Computer                 50W             100W        N/A 
Lawnmower                       1000W           1400W       N/A 
LED Light Bulb                  7W              10W         0W          [1][2]
Microwave                       600W            1700W       3W          [1][2]
Oven                            2150W           2150W       N/A 
Power Shower                    7500W           10500W      N/A 
Rice Cooker                     200W            250W        N/A 
Scanner                         10W             18W         N/A 
Smart Phone Charger             4W              7W          N/A 
Strimmer                        300W            500W        N/A 
Submersible Water Pump          400W            400W        N/A 
Table Fan                       10W             25W         N/A 
Tablet Charger                  10W             15W         N/A 
Tablet Computer                 5W              10W         N/A         [1]
Toaster                         800W            1800W       0W          [1]
TV (19" colour)                 40W             100W        1W          [1]
Vacuum Cleaner                  200W            700W        0W  
Washing Machine                 500W            500W        N/A 
Water Dispenser                 100W            100W        N/A         [1]
Water Feature                   35W             35W         N/A 
Water Filter and Cooler         70W             100W        N/A         [1]
'''





'''
    dict_cases = {0:None, 
                1:'no_ldc',
                2:'ripple_control',
                3:'loading_50', 
                4:'loading_75', 
                5:'loading_auto', 
                6:'per_house',  # adoption 50, target auto
                7:'per_device', # adoption 50, target auto
                8:'adoption_10',
                9:'adoption_20',
                10:'adoption_30',
                11:'adoption_40',
                12:'adoption_50',
                13:'adoption_60',
                14:'adoption_70',
                15:'adoption_80',
                16:'adoption_90',
                17:'adoption_100',
                18:'basic_ldc_waterheater',
                19:'basic_ldc_dynamic',  
                20:'advanced_ldc',
                21:'loading_avg1h',
                22:'resolution_1hz',
                23:'resolution_10hz',
                24:'resolution_1uhz',
                25:'loading_30',

                31:'ideal_direct_k32_tou_step100ms',
                32:'ideal_direct_k32_tou_step1s',
                33:'ideal_direct_k32_tou_step5s',
                34:'ldc_direct_k32_t50_step1s_halfdb', # duration is 1.75 day
                35:'ldc_setpoint_k32_t50_step1s_halfdb', # duration is 1.75 day
                
                101:'ramp_direct_k16_t100_d0s',
                102:'ramp_direct_k32_t100_d0s',
                103:'ramp_direct_k64_t100_d0s',
                104:'ramp_direct_k128_t100_d0s',
                105:'ramp_direct_k256_t100_d0s',
                106:'ramp_direct_k512_t100_d0s',
                107:'ramp_direct_k1024_t100_d0s',
                108:'ramp_direct_k2048_t100_d0s',
                109:'ramp_direct_k4096_t100_d0s',
                110:'ramp_direct_k8192_t100_d0s',
                
                111:'ramp_direct_k16_t100_d1s',
                112:'ramp_direct_k32_t100_d1s',
                113:'ramp_direct_k64_t100_d1s',
                114:'ramp_direct_k128_t100_d1s',
                115:'ramp_direct_k256_t100_d1s',
                116:'ramp_direct_k512_t100_d1s',
                117:'ramp_direct_k1024_t100_d1s',
                118:'ramp_direct_k2048_t100_d1s',
                119:'ramp_direct_k4096_t100_d1s',
                110:'ramp_direct_k8192_t100_d1s',
                
                121:'ideal_direct_k16_tou',
                122:'ideal_direct_k32_tou',
                123:'ideal_direct_k64_tou',
                124:'ideal_direct_k128_tou',
                125:'ideal_direct_k256_tou',
                126:'ideal_direct_k512_tou',
                127:'ideal_direct_k1024_tou',
                128:'ideal_direct_k2048_tou',
                129:'ideal_direct_k4096_tou',
                130:'ideal_direct_k8192_tou',
                

                131:'ideal_setpoint_k16_tou',
                132:'ideal_setpoint_k32_tou',
                133:'ideal_setpoint_k64_tou',
                134:'ideal_setpoint_k128_tou',
                135:'ideal_setpoint_k256_tou',
                136:'ideal_setpoint_k512_tou',
                137:'ideal_setpoint_k1024_tou',
                138:'ideal_setpoint_k2048_tou',
                139:'ideal_setpoint_k4096_tou',
                140:'ideal_setpoint_k8192_tou',
                

                141:'ideal_setpoint2_k16_tou',
                142:'ideal_setpoint2_k32_tou',
                143:'ideal_setpoint2_k64_tou',
                144:'ideal_setpoint2_k128_tou',
                145:'ideal_setpoint2_k256_tou',
                146:'ideal_setpoint2_k512_tou',
                147:'ideal_setpoint2_k1024_tou',
                148:'ideal_setpoint2_k4096_tou',
                149:'ideal_setpoint2_k8192_tou',
                
                
                200:'ideal_mixed_no_ldc',
                201:'ideal_mixed_k16_tou',
                202:'ideal_mixed_k32_tou',
                203:'ideal_mixed_k64_tou',
                204:'ideal_mixed_k128_tou',
                205:'ideal_mixed_k256_tou',
                206:'ideal_mixed_k512_tou',
                207:'ideal_mixed_k1024_tou',
                208:'ideal_mixed_k2048_tou',
                209:'ideal_mixed_k90_tou',
                210:'ideal_mixed_k100_tou',
                
                211:'ideal_mixed2_k10_tou',
                212:'ideal_mixed2_k20_tou',
                213:'ideal_mixed2_k30_tou',
                214:'ideal_mixed2_k40_tou',
                215:'ideal_mixed2_k50_tou',
                216:'ideal_mixed2_k60_tou',
                217:'ideal_mixed2_k70_tou',
                218:'ideal_mixed2_k80_tou',
                219:'ideal_mixed2_k90_tou',
                220:'ideal_mixed2_k100_tou',

                223:'delayed_mixed_k256_50',
                }
'''