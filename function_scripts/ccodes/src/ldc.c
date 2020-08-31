#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <pthread.h>
#include "server.h"
#include "log.h"

#include "chroma.h"
#include "switch.h"
#include "power.h"

#include <unistd.h>			//Used for UART
#include <fcntl.h>			//Used for UART
#include <termios.h>		//Used for UART
#include "serial.h"
#include "ldc.h"
#include <pigpio.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <net/if.h>
#include <arpa/inet.h>


struct rpi_t data;
pthread_barrier_t barr;
int unit_node_id = ID_NODE;

void handler_rec(char* packet, int size);


long conv_ms_ns(int ms) {
	return ms * 1000000;
}


void handler_rec_barrier(char *packet, int size) {
	handler_rec(packet, size);
	pthread_barrier_wait(&barr);
}


void handler_rec(char* packet, int size) {
	int i;
	char msgs[200] = {'\0'};
	char msg[5];
	for(i=0; i<size; i++){
		sprintf(msg, "%02X ", packet[i] & 0xff);
		strcat(msgs, msg);
	}
	log_info("Received %s", msgs);
	data.group = packet[2] & 0xff;
	data.node = packet[1] & 0xff;
	data.type = packet[4] & 0xff;
	data.data = ((packet[5] << 8) | (packet[6] & 0xff)) & 0xffff;
}


void handler_send(char* packet, int size) {
	int i;
	char msgs[200] = {'\0'};
	char msg[5];
	for(i=0; i<size; i++){
		sprintf(msg, "%02X ", packet[i] & 0xff);
		strcat(msgs, msg);
	}
	log_info("Sent %s", msgs);
	data.group = packet[9] & 0xff;
	data.node = packet[10] & 0xff;
	data.type = packet[11] & 0xff;
	data.data = ((packet[12] << 8) | (packet[13] & 0xff)) & 0xffff;
}

/* Returns the interface IP Address
   Params: int iNetType - 0: ethernet, 1: Wifi
           char *chIP - IP Address string
   Return: 0: success / -1: Failure
    */
int getIpAddress() {
  struct ifreq ifr;
  int sock = 0;
  char chIP[16];
 
  sock = socket(AF_INET, SOCK_DGRAM, 0);
  strcpy(ifr.ifr_name, "wlan0");
  if (ioctl(sock, SIOCGIFADDR, &ifr) < 0) {
    strcpy(chIP, "0.0.0.0");
    return -1;
  }
  sprintf(chIP, "%s", inet_ntoa(((struct sockaddr_in *) &(ifr.ifr_addr))->sin_addr));
  close(sock);
  printf("IP: %s\n", chIP);
  return 0;
}

/*
inet_ntoa(
  (
    (struct sockaddr_in *) &(ifr.ifr_addr)
  )->sin_addr
)
*/

int main(int argc, char* arg[]) {
	pthread_t ems_thread;
	int x=0;
	
	getIpAddress();
	
	gpioInitialise();
	gpioSetMode(GPIO_LED_RED,    PI_OUTPUT);  // set AC switch as output
	gpioSetMode(GPIO_LED_ORANGE, PI_OUTPUT);  // set AC switch as output
	gpioSetMode(GPIO_LED_GREEN,  PI_OUTPUT);  // set AC switch as output
	gpioSetMode(GPIO_485_DIR,    PI_OUTPUT);  // set AC switch as output
	gpioWrite(GPIO_485_DIR, 0);	
	
	for(x=0; x<3; x++){
		gpioWrite(GPIO_LED_RED,    1);	
		gpioWrite(GPIO_LED_ORANGE, 1);	
		gpioWrite(GPIO_LED_GREEN,  1);	
		gpioDelay(100000);
		gpioWrite(GPIO_LED_RED,    0);	
		gpioWrite(GPIO_LED_ORANGE, 0);	
		gpioWrite(GPIO_LED_GREEN,  0);	
		gpioDelay(100000);
	}
	gpioWrite(GPIO_LED_GREEN,  1);	

	if(argc > 1 && strcmp(arg[1], "power") == 0){
		//~ struct rpi_t p;
		ems_thread = ems_run_server(3000, handler_rec_power);
		//~ uint16_t freq = 0;

		power_init();
		//~ pthread_create(&power, NULL, sendpower, &period);
		while(1){
			//~ getchar();
			//~ p.group	= 12;
			//~ p.node = 201;
			//~ p.type = 13;
			//~ p.data = ++freq;
			//~ log_debug("## Sending packet group: %d, node: %d, type: %d, data: %d",p.group, p.node, p.type, p.data);
			//~ ems_send(&p);
			//~ p.group	= 12;
			//~ p.node = 201;
			//~ p.type = 14;
			//~ p.data = ++freq;
			//~ ems_send(&p);
			//~ p.group	= 12;
			//~ p.node = 201;
			//~ p.type = 15;
			//~ p.data = ++freq;
			//~ ems_send(&p);
			//~ p.group	= 12;
			//~ p.node = 101;
			//~ p.type = 12;
			//~ p.data = ++freq;
			//~ ems_send(&p);
		}
		ems_destroy(ems_thread);
	}
	else if(argc > 1 && strcmp(arg[1], "switch") == 0){
		if(argc > 2 && strncmp(arg[2], "tty", 3) == 0){
			if(argc > 3){
				unit_node_id = atoi(arg[3]);
			}
    		printf("ID: %d\n", unit_node_id);
			ems_thread = ems_run_server(3000, handler_rec_switch);
			switch_init(arg[2]);
			while(1){
				switch_proc();
			}
		}
		else
			printf("...tty?\n");
	}
	else if(argc > 1 && strcmp(arg[1], "chroma") == 0){
		if(argc < 4)
			printf("Usage: ldc chroma tty485 tty232\n");
		else{
			ems_thread = ems_run_server(3000, handler_rec_chroma);
			chroma_init(arg[2], arg[3]);
			while(1){
			}
		}

	}
	else
		printf("usage...\n");
	
}



