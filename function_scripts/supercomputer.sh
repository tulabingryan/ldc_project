yes | sudo apt-get install gfortran &&
mkdir /home/pi/mpich3/ &&
cd /home/pi/mpich3/ &&
wget http://www.mpich.org/static/downloads/3.3/mpich-3.3.tar.gz &&
tar xfz mpich-3.3.tar.gz &&
sudo mkdir /home/rpimpi/ &&
sudo mkdir /home/rpimpi/mpich3-install &&
sudo mkdir /home/pi/mpich_build &&
cd /home/pi/mpich_build &&
sudo /home/pi/mpich3/mpich-3.3/configure -prefix=/home/rpimpi/mpich3-install &&
sudo make &&
sudo make install


# to send command via ssh 
# ssh -n -f pi@192.168.3.103 "sh -c 'cd /home/pi/ldc_project/function_scripts; nohup sh supercomputer.sh > /dev/null 2>&1 &'"


