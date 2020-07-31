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



int spi_psoc_fd = -1;


int power_level = 0;
int ldc_freq = 0;
int ldc_priority = 100;  //XXX test




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


void ldc_freq_meas(void)
{
	int ldc_level =  0;
	
   while (1)
   {
		ldc_level = get_ldc();
		if(ldc_level > 100)
			ldc_level = 100;
		printf(" LDC:%d\n", ldc_level);
		
		//if((ldc_priority==0) || (power_level == 0))
		//	set_ac_switch(0);
		//else if (power_level > 0){
		//	if( (ldc_priority == 100) || (ldc_level >= (100-ldc_priority)) )
		//	  set_ac_switch(1);
		//	else if ( (ldc_level==0) || ((ldc_level+LDC_HYSTERESIS) < (100-ldc_priority)) )
		//	  set_ac_switch(0);
		//}
		//gpioWrite(GPIO_LED_ORANGE, 0);	
		//gpioDelay(125000);
		//gpioWrite(GPIO_LED_ORANGE, 1);	
		//gpioDelay(125000);
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



int main(){
	int r=0;
	spi_ldc_init();
	ldc_freq_meas();

}
