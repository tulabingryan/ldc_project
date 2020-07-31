#include "ldc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "switch.h"
#include "log.h"
#include "server.h"
#include "serial.h"

#include <unistd.h>			// Used for UART
#include <termios.h>		// Used for UART
#include <sys/ioctl.h>
#include <fcntl.h>

#include <pigpio.h>
#include <linux/spi/spidev.h>

#define LDC_HYSTERESIS 5


int spi_psoc_fd = -1;


int power_level = 0;
int ldc_freq = 0;
int ldc_priority = 100;  //XXX test
pthread_t ldc_freq_thread;
void* ldc_freq_meas(void* argument);
int switch_state = 0;


void handler_rec_switch(char* packet, int size) {
	struct rpi_t data;
	int i;
	char msgs[200] = {'\0'};
	char msg[5];
	for(i=0; i<size; i++){
		sprintf(msg, "%02X ", packet[i] & 0xff);
		strcat(msgs, msg);
	}
	log_info("SWITCH: Received %s", msgs);
	data.group = packet[2] & 0xff;
	data.node = packet[1] & 0xff;
	data.type = packet[4] & 0xff;
	data.data = ((packet[7] << 8) | (packet[8] & 0xff)) & 0xffff;
	if( (data.type == REC_TYPE_POWER) && (data.data <= 4095) ){
		power_level = data.data;
		log_info("[SWITCH] Power:%d\n", power_level);
	}
	else if( (data.type == REC_TYPE_PRIORITY) && (data.data <= 100) ){
		ldc_priority = (data.data);
		log_info("[SWITCH] Priority:%d\n", ldc_priority);
	}
}


void send_power(int fd, int reply_power)
{
	int length = 0;
	char poll_buffer[10];
	extern int unit_node_id;

	gpioWrite(GPIO_485_DIR, 1);	

	poll_buffer[length++]=ID_GROUP;//(char)(group & 0x00ff);
	poll_buffer[length++]=unit_node_id; //ID_NODE; //(char)(node  & 0x00ff);
	poll_buffer[length++]=PWR_REPLY;
	poll_buffer[length++]=(char)(reply_power >> 8);
	poll_buffer[length++]=(char)(reply_power & 0x00ff);


	// clear the incoming buffer
	tcflush(uart_rs485_filestream, TCIFLUSH);
	serial_send_485(uart_rs485_filestream, poll_buffer, length);
// wait for data to send	
	gpioDelay(2000);
	gpioWrite(GPIO_485_DIR, 0);	

}


void rec_485_data(int fd)
{
	int bytes = 0;
	char rec_buffer[100];
	char rec_byte = 0;
	static char data_buffer[100];
    int i;
    static enum {REC_START_WAIT, REC_DATA, REC_DLE, REC_END} rec_state = REC_START_WAIT;
    static int rec_ptr = 0;
	int group = 0;
	int node = 0;
	int type = 0;
	extern int unit_node_id;
	
	ioctl(fd, FIONREAD, &bytes);
	if(bytes==0)
		return;
	int count = read(fd, rec_buffer, bytes);

	i=0;
	while(i<count){
		rec_byte = rec_buffer[i++];
		switch(rec_state){
			case REC_START_WAIT:
				if(rec_byte == STX)
					rec_state = REC_DATA;
				break;
			case REC_DATA:
				if(rec_byte == DLE)
					rec_state = REC_DLE;
				else if(rec_byte == ETX)
					rec_state = REC_END;
				else
					data_buffer[rec_ptr++] = rec_byte;
				break;
			case REC_DLE:
				data_buffer[rec_ptr++] = rec_byte ^ 0x80;
				rec_state = REC_DATA;
				break;
			case REC_END:  // redundant
				break;
		}
	}
	
	// return packet, or parse here?
	if(rec_state == REC_END){
		rec_state = REC_START_WAIT;
		rec_ptr = 0;
		group = data_buffer[0];
		node = data_buffer[1];
		type = data_buffer[2];
		// send reply (power)
		if( (type == PWR_POLL) && (group == ID_GROUP) && (node == unit_node_id) ){
			if(switch_state==1)
				send_power(fd, power_level);
			else
				send_power(fd, 0);
//			log_info("[SWITCH] Polled power:%d", power_level);
		}
	}
}


void set_ac_switch(int state)
{
	if(state){
		gpioWrite(GPIO_ACSW, 1);	// turn AC switch on
		switch_state = 1;
	}
	else{
		gpioWrite(GPIO_ACSW, 0);	// turn AC switch off
		switch_state = 0;
	}
}


// Read LDC parameter (0-100) from psoc on SPI
int get_ldc(void)
{
	int ret;
	uint8_t tx[3] = {0x00, 0x00, 0x00};
	uint8_t rx[3] = {0, };
	struct spi_ioc_transfer tr = {
		.tx_buf = (unsigned long)tx,
		.rx_buf = (unsigned long)rx,
		.len = 1,
		.delay_usecs = 0,
		.speed_hz = 500000,
		.bits_per_word = 8,
	};
	
	tx[0] = 0xCA;   // dummy data for read 11001010
	ret = ioctl(spi_psoc_fd, SPI_IOC_MESSAGE(1), &tr);
	if (ret < 1)
		perror("Can't send psoc spi message");

	ret = rx[0]; 
	return ret;
}


void* ldc_freq_meas(void* argument)
{
	int ldc_level =  0;
	
   while (1)
   {
		ldc_level = get_ldc();
		if(ldc_level > 100)
			ldc_level = 100;
//		printf(" LDC:%d\n", ldc_level);
		if((ldc_priority==0) || (power_level == 0))
			set_ac_switch(0);
		else if (power_level > 0){
			if( (ldc_priority == 100) || (ldc_level >= (100-ldc_priority)) )
			  set_ac_switch(1);
			else if ( (ldc_level==0) || ((ldc_level+LDC_HYSTERESIS) < (100-ldc_priority)) )
			  set_ac_switch(0);
		}
		gpioWrite(GPIO_LED_ORANGE, 0);	
		gpioDelay(125000);
		gpioWrite(GPIO_LED_ORANGE, 1);	
		gpioDelay(125000);
   }
}


void spi_ldc_init(void)
{
	int bits = 8;
	int speed = 500000;
//	int mode = 3;
	int mode = 3;
	int ret = 0;

	spi_psoc_fd = open("/dev/spidev0.0", O_RDWR);
	if (spi_psoc_fd < 0){
		perror("Can't open SPI device");
		abort();
	}
	// spi mode
	ret = ioctl(spi_psoc_fd, SPI_IOC_WR_MODE, &mode);
	if (ret == -1){
		perror("Can't set spi WR mode");
		abort();
    }
	// spi mode
	ret = ioctl(spi_psoc_fd, SPI_IOC_RD_MODE, &mode);
	if (ret == -1){
		perror("Can't set spi RD mode");
		abort();
    }
	// bits per word
	ret = ioctl(spi_psoc_fd, SPI_IOC_WR_BITS_PER_WORD, &bits);
	if (ret == -1){
		perror("Can't set bits per word");
		abort();
	}
	// max speed hz
	ret = ioctl(spi_psoc_fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed);
	if (ret == -1){
		perror("Can't set max speed hz");
		abort();
	}
}


void switch_init(char* tty){
	char dev485[15]="/dev/ttyUSB0";
	int ldc_arg = 0;
	
	sprintf(dev485, "/dev/%s", tty);
	uart_rs485_filestream  = tty_open(dev485);
	spi_ldc_init();

//	gpioInitialise();

	gpioSetMode(GPIO_ACSW, PI_OUTPUT);  // set AC switch as output
	gpioSetPullUpDown(GPIO_ACSW, PI_PUD_UP); // enable pullup on AC switch output
	gpioWrite(GPIO_ACSW, 1);	// turn AC switch on

	pthread_create(&ldc_freq_thread, NULL, ldc_freq_meas, &ldc_arg);
}


void switch_close(void)
{
	tty_close(uart_rs485_filestream);
}


void switch_proc(void)
{
	rec_485_data(uart_rs485_filestream);
}
