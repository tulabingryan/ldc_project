# Run this file as
# bash install_berryconda.sh

chmod +x /home/pi/ldc_project/required_packages/Berryconda3-2.0.0-Linux-armv6l.sh
/home/pi/ldc_project/required_packages/Berryconda3-2.0.0-Linux-armv6l.sh -b
export PATH=/home/pi/berryconda3/bin:$PATH &&
export PATH=/home/pi/berryconda3/bin:$PATH &&
export PATH=/home/pi/berryconda3/bin:$PATH && yes | conda install numpy scipy pandas pytables&&
pip install geocoder pyserial RPi.GPIO pifacedigitalio pifacecommon spidev && 
pip install -r requirements.txt && sudo reboot&


