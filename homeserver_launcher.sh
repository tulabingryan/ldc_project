#./homeserver_launcher.sh
# autorun the python programs
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts && python delay.py &&
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts && python run_cmd.py & 
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts && python operative.py & 
# export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/ldc_homeserver/history && python email_file.py & 
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/ldc_homeserver && python read_sensors.py & 

