# Instructions to run the LDC Server
# After installation of required dependencies as 
# detailed in setup_procedure.txt

# 1. Run the MAIN.py in the folder 'ldc_system'
python /home/pi/ldc_project/ldc_system/MAIN.py
# 2. Run the script that will send query to load status
python /home/pi/ldc_project/grid_server/update_ldc_db.py

# 3. Run the sever app
python /home/pi/ldc_project/grid_server/server_app.py
