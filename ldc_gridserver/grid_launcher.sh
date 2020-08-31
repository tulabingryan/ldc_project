#./grid_launcher.sh
# delay all autorun scripts to allow loading up of dependencies
#export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts/ && python delay.py  # delay other processes below
# autorun the IP checker
export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_project/function_scripts/ && python email_public_ip.py&  # check changes in public ip address and email changes
# # run simulation
# export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_system/ && python MAIN.py&   # run ardmore simulation
# # run aggregator
# export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_system/ && python AGG.py&  # aggregate data from simulation
# # run data logger 1
# export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_gridserver/ && python data_logger.py&  # save data to ldc_agg_flat.db
# run data logger 2
export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_project/ldc_gridserver/ && python data_logger2.py&  # save data to ldc_agg_melted.db
# run grid server
export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/ldc_project/ldc_gridserver/ &&  python grid_server.py&  # grid server gui

# run load profile viewer
export PATH=/home/pi/anaconda3/bin:$PATH && cd /home/pi/load_profiles/ && python app.py&  # load profiles gui

