#./simulate.sh
# This script runs multiple simulation cases in sequence
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 2 --case 1 --adoption 1 --target auto --algorithm no_ldc --distribution per_house --ranking static  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 2 --case 2 --adoption 1 --target auto --algorithm scheduled_ripple --distribution per_house --ranking static  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 2 --case 3 --adoption 1 --target 50 --algorithm basic_ldc --distribution per_house --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 2 --case 4 --adoption 1 --target 75 --algorithm basic_ldc --distribution per_house --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 5 --adoption 1.0 --target auto --algorithm basic_ldc --distribution per_house --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 6 --adoption 0.5 --target auto --algorithm basic_ldc --distribution per_house --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 7 --adoption 0.5 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 8 --adoption 0.1 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 9 --adoption 0.2 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 10 --adoption 0.3 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 11 --adoption 0.4 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# # cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 12 --adoption 0.5 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 13 --adoption 0.6 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# # cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 14 --adoption 0.7 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 15 --adoption 0.8 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 16 --adoption 0.9 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 17 --adoption 1.0 --target auto --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 18 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_device --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 19 --adoption 1.0 --target auto --algorithm basic_ldc --distribution per_device --ranking dynamic   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 3 --network 2 --case 20 --adoption 1.0 --target auto --algorithm advanced_ldc --distribution per_device --ranking dynamic  &&


### for exploring different resolution of ldc_signal sensor
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 1 --timestep 1 --network 1 --case 23 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_house --ranking static  &&  # resolution is 10 hz
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 1 --timestep 1 --network 1 --case 22 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 0  &&  # resolution is 1 hz
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 1 --timestep 1 --network 1 --case 24 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 6  &&  # resolution is 1 micro hz

# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 1 --timestep 1 --network 2 --case 23 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_house --ranking static  &&  # resolution is 10 hz
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 1 --timestep 1 --network 2 --case 22 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 0  &&  # resolution is 1 hz
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 1 --timestep 1 --network 2 --case 24 --adoption 1.0 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 6  &&  # resolution is 1 micro hz



# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 1 --case 3 --adoption 1 --target 50 --algorithm basic_ldc --distribution per_house --ranking static   &&

### dickert_lv_long
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 3 --case 3 --adoption 1 --target 50 --algorithm basic_ldc --distribution per_house --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 3 --case 1 --adoption 1 --target auto --algorithm no_ldc --distribution per_house --ranking static  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 3 --case 4 --adoption 1 --target 75 --algorithm basic_ldc --distribution per_house --ranking static   &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 7 --timestep 1 --network 3 --case 2 --adoption 1 --target auto --algorithm scheduled_ripple --distribution per_house --ranking static  &&

### ieee_european_lv
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 0.1 --network 4 --case 25 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 1  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 0.1 --network 4 --case 20 --adoption 1 --target 30 --algorithm advanced_ldc --distribution per_device --ranking dynamic --resolution 1  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 0.1 --network 4 --case 19 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_device --ranking dynamic --resolution 1  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 0.1 --network 4 --case 3 --adoption 1 --target 50 --algorithm basic_ldc --distribution per_house --ranking static --resolution 1  &&
# # cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 1 --network 4 --case 4 --adoption 1 --target 75 --algorithm basic_ldc --distribution per_house --ranking static --resolution 1  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 1 --network 4 --case 2 --adoption 1 --target tou --algorithm ripple_control --distribution per_house --ranking static --resolution 1 &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 1 --network 4 --case 18 --adoption 1 --target 40 --algorithm basic_ldc --distribution per_house --ranking static --resolution 1  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.1 --timestep 1 --network 4 --case 1 --adoption 1 --target auto --algorithm no_ldc --distribution per_house --ranking static  --resolution 1 &&



### Ki studies
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 200 --tcl_control mixed --adoption 1 --target tou --algorithm no_ldc --distribution per_house --ranking static --resolution 3  &&
## ramp tests
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 101 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 102 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 103 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 104 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 105 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 106 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 107 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 108 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 109 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 110 --adoption 1 --target 100 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 111 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 112 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 113 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 114 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 115 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 116 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 117 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 118 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 119 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 120 --adoption 1 --target 30 --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

### direct control of TCL
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 121 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 122 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 123 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 124 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 125 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 126 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 127 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 128 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 129 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 130 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

### setpoint control of TCL
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 131 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 132 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 133 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 134 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 135 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 136 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 137 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 138 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 139 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 140 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

### setpoint2 control of TCL
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 141 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 142 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 143 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 144 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 145 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 146 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 147 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 148 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 149 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 150 --tcl_control setpoint2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 201 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 202 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 203 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 204 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 205 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 206 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 207 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 208 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 209 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 210 --tcl_control mixed --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 4 --case 211 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 4 --case 212 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 4 --case 213 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 4 --case 214 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 4 --case 215 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 4 --case 216 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 4 --case 217 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 4 --case 218 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 4 --case 219 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 4 --case 220 --tcl_control mixed2 --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&


### lv 5
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 1 --case 121 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 1 --case 122 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 1 --case 123 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 1 --case 124 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 1 --case 125 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 1 --case 126 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 1 --case 127 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 1 --case 128 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 1 --case 129 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 1 --case 130 --tcl_control direct --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&

# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 10 --network 1 --case 131 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 20 --network 1 --case 132 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 30 --network 1 --case 133 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 40 --network 1 --case 134 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 50 --network 1 --case 135 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 60 --network 1 --case 136 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 70 --network 1 --case 137 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 80 --network 1 --case 138 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 90 --network 1 --case 139 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 1 --days 0.05 --timestep 0.1 --ki 100 --network 1 --case 140 --tcl_control setpoint --adoption 1 --target tou --algorithm basic_ldc --distribution per_house --ranking static --resolution 3  &&
	
  ### decrease resolution

# 1:'no_ldc',
# 2:'ripple_control',
# 3:'loading_50', 
# 4:'loading_75', 
# 5:'loading_auto', 
# 6:'per_house',  # adoption 50, target auto
# 7:'per_device', # adoption 50, target auto
# 8:'adoption_10',
# 9:'adoption_20',
# 10:'adoption_30',
# 11:'adoption_40',
# 12:'adoption_50',
# 13:'adoption_60',
# 14:'adoption_70',
# 15:'adoption_80',
# 16:'adoption_90',
# 17:'adoption_100',
# 18:'basic_ldc_waterheater',
# 19:'basic_ldc_dynamic', 
# 20:'advanced_ldc'}
### summer
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 3 --adoption 1 --target auto &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 4 --adoption 1 --target auto &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 5 --adoption 1 --target 50 &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 5 --adoption 1 --target 75 &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 5 --adoption 1 --target auto &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 6 --adoption 1 --target 50 &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 6 --adoption 1 --target 75 &&
# cd /home/pi/ldc_project/ldc_simulator/ && /home/pi/anaconda3/bin/python MAIN.py --simulate 1 --season 2 --days 7 --timestep 10 --network 2 --case 6 --adoption 1 --target auto &&
### end
cd /home/pi/ldc_project/ldc_simulator/