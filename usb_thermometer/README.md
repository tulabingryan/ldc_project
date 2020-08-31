usb-thermometer: TEMPer1 and TEMPer1F
===============

### From Pete Chapman:

* Fixed poor precision for TEMPer1F (iProduct string "TEMPer1F_V1.3").

### From Peter Vojtek:

The original version of pcsensor0.0.1 was located on [this page](http://bailey.st/blog/2012/04/12/dirt-cheap-usb-temperature-sensor-with-python-sms-alerting-system/). I took the source code and fixed following bug:

* temperatures below zero overflow: 254.3 C is displayed instead of -1.3 C, .

### How to run it

1. clone this repository
2. `$ sudo apt-get install libusb-dev`
3. `$ make`
4. connect the thermometer
5. `$ sudo ./pcsensor`

The output looks like:

```
2014/10/30 07:00:36 Temperature 73.96F 23.31C
```


#### Updated instructions how to use  (as of 2019-09-12)
$ apt-get install build-essential libusb-dev
$ unzip master.zip (or whatever the driver zip file is)
$ cd usb-thermometer-master
$ make
$ sudo make rules-install
Unplug and Re-Plug the Thermometer
$ ./pcsensor

### Notes:
There are cases that vendor id and product id is different from the constants declared in the ccode. First get the correct ids by
lsusb
output is ID 413d:2107 which is
then update
#define VENDOR_ID  0x413d
#define PRODUCT_ID 0x2107