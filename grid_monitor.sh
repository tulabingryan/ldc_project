#./grid_monitor.sh
# autorun the emailer
#cd /home/pi/ldc_project/ldc_gridserver/history/ && sudo /home/pi/berryconda3/bin/python email_file.py&
# autorun the 'update_ldc_db.py: to query home demands and status and save in ldc.db

cd /home/pi/ldc_project/function_scripts/ && /home/pi/berryconda3/bin/python operative.py &
cd /home/pi/ldc_project/ldc_gridserver/ && /home/pi/berryconda3/bin/python tcp_server.py & 
cd /home/pi/ldc_project/ && /home/pi/berryconda3/bin/python update_config.py &
cd /home/pi/ldc_project/ && /home/pi/berryconda3/bin/python send_data.py &

