#./install_pcsensor.sh
yes | sudo apt-get install build-essential libusb-dev
make
sudo make rules-install
sudo cp pcsensor /usr/local/bin
