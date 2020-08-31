#include "ldc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "power.h"
#include "log.h"
#include "server.h"

#include <stdint.h>
#include <fcntl.h>

#include <sys/ioctl.h>
#include <linux/types.h>
#include <linux/spi/spidev.h>




#define M90E26_ADDR_L_CURRENT 			0x48
#define M90E26_ADDR_VOLTAGE 				0x49
#define M90E26_ADDR_L_MEAN_ACTIVE_P		0x4A
#define M90E26_ADDR_L_MEAN_REACTIVE_P	0x4B
#define M90E26_ADDR_FREQ					0x4C
#define M90E26_ADDR_POWER_FACTOR			0x4D
#define M90E26_ADDR_PHASE_ANGLE			0x4E
#define M90E26_ADDR_APPARENT_POWER  	0x4F

#define M90E26_ADDR_N_CURRENT				0x68


pthread_t power_thread;
void* sendpower(void* argument);
int reporting_period = POWER_REPORTING_PERIOD;
int spi_fd = -1;


void handler_rec_power(char* packet, int size) {
	//~ struct rpi_t data;
	int i;
	char msgs[200] = {'\0'};
	char msg[5];
	for(i=0; i<size; i++){
		sprintf(msg, "%02X ", packet[i] & 0xff);
		strcat(msgs, msg);
	}
	log_info("POWER: Received %s", msgs);
	//~ data.group = packet[2] & 0xff;
	//~ data.node = packet[1] & 0xff;
	//~ data.type = packet[4] & 0xff;
	//~ data.data = ((packet[5] << 8) | (packet[6] & 0xff)) & 0xffff;
}


void power_init(void){
	int bits = 8;
	int speed = 500000;
	int mode = 3;
	int ret = 0;
	
//	int reporting_period = POWER_REPORTING_PERIOD;
	log_info("POWER: reporting period %d", reporting_period);
	pthread_create(&power_thread, NULL, sendpower, &reporting_period);
	
	spi_fd = open("/dev/spidev0.1", O_RDWR);
	if (spi_fd < 0){
		perror("Can't open SPI device");
		abort();
	}
	// spi mode
	ret = ioctl(spi_fd, SPI_IOC_WR_MODE, &mode);
	if (ret == -1)
		perror("Can't set spi mode");

	// bits per word
	ret = ioctl(spi_fd, SPI_IOC_WR_BITS_PER_WORD, &bits);
	if (ret == -1)
		perror("Can't set bits per word");

	// max speed hz
	ret = ioctl(spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);
	if (ret == -1)
		perror("Can't set max speed hz");

}


// read from M90E26
int m90e26_read(int address){
	int ret;
	uint8_t tx[3] = {0x00, 0x00, 0x00};
	uint8_t rx[3] = {0, };
	struct spi_ioc_transfer tr = {
		.tx_buf = (unsigned long)tx,
		.rx_buf = (unsigned long)rx,
		.len = 3,
		.delay_usecs = 0,
		.speed_hz = 500000,
		.bits_per_word = 8,
	};
	
	tx[0] = address | 0x80;   // first bit sent sets R/W mode. Read=1.
	ret = ioctl(spi_fd, SPI_IOC_MESSAGE(1), &tr);
	if (ret < 1)
		perror("Can't send spi message");

	ret = (rx[1]<<8)+rx[2];
	return ret;
}


// write to M90E26
void m90e26_write(int address, int data){
	int ret;
	uint8_t tx[3] = {0x00, 0x00, 0x00};
	uint8_t rx[3] = {0, };
	struct spi_ioc_transfer tr = {
		.tx_buf = (unsigned long)tx,
		.rx_buf = (unsigned long)rx,
		.len = 3,
		.delay_usecs = 0,
		.speed_hz = 500000,
		.bits_per_word = 8,
	};
	
	tx[0] = address & 0x7f;   // first bit sent sets R/W mode. Write=0.
	tx[1] = (uint8_t)((data & 0xff00) >> 8);
	tx[2] = (uint8_t) (data & 0x00ff);
	ret = ioctl(spi_fd, SPI_IOC_MESSAGE(1), &tr);
	if (ret < 1)
		perror("Can't send spi message");
}


// initialise the power monitor IC and spi
int m90e25_init(void)
{
	// configuration and calibration 
	//~ m90e25_write();
	return 0;
}


// read power, current, voltage from spi (ATM90E25)
int read_power(int* current, int* voltage, int* power)
{
  static int dummy_power   = 1000;
  static int dummy_voltage = 230;
  static int dummy_current = 10;

  static int meas_power   = 0;
  static int meas_voltage = 0;
  static int meas_current = 0;

  meas_power   = m90e26_read(M90E26_ADDR_APPARENT_POWER);
  meas_current = m90e26_read(M90E26_ADDR_L_CURRENT);
  meas_voltage = m90e26_read(M90E26_ADDR_VOLTAGE);

  if(++dummy_power >= 1010)
    dummy_power = 1000;
  *power = dummy_power;
  *power = meas_power;

  if(++dummy_voltage >= 240)
    dummy_voltage = 230;
  *voltage = dummy_voltage;
  *voltage = meas_voltage;

  if(++dummy_current >= 15)
    dummy_current = 10;
  *current = dummy_current;
  *current = meas_current;

  return 0;
}


void* sendpower(void* argument) {
  struct rpi_t p;
  int sleep_period;
  int current = 0;
  int voltage = 0;
  int power = 0;
  
  sleep_period = *((int*)argument);
  log_debug("POWER: sleep %d", sleep_period);
  
  while(1){
    read_power(&current, &voltage, &power);

	p.group	= ID_GROUP;
	p.node = ID_NODE;
	p.type = SEND_TYPE_VOLTAGE;
	p.data = voltage;
	log_debug("## Sending Voltage: Group:%d, Node:%d, Type:%d, Data:%d",p.group, p.node, p.type, p.data);
	ems_send(&p);
	p.group	= ID_GROUP;
	p.node = ID_NODE;
	p.type = SEND_TYPE_CURRENT;
	p.data = current;
	log_debug("## Sending Current: Group:%d, Node:%d, Type:%d, Data:%d",p.group, p.node, p.type, p.data);
	ems_send(&p);
	p.group	= ID_GROUP;
	p.node = ID_NODE;
	p.type = SEND_TYPE_POWER;
	p.data = power;
	log_debug("## Sending Power: Group:%d, Node:%d, Type:%d, Data:%d",p.group, p.node, p.type, p.data);
	ems_send(&p);

	sleep(sleep_period);
//	sleep(2);
  }
 
  return NULL;
}


