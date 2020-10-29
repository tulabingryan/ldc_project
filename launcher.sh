#./launcher.sh
# autorun the python programs in raspberry pi
#export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/ && python initialize_config.py &&
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts && python delay.py &&
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts && python run_cmd.py & 
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/ && python update_config.py &
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/ && python send_data.py & 
export PATH=/home/pi/berryconda3/bin:$PATH && cd /home/pi/ldc_project/ldc_simulator && python MAIN.py & 

