#include "ldc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>			//Used for UART
#include <fcntl.h>			//Used for UART
#include <termios.h>		//Used for UART

#include "chroma.h"
#include "log.h"
#include "server.h"
#include "serial.h"
#include <pigpio.h>

//#define _GNU_SOURCE  
//#include <signal.h>
//#include <poll.h>

// RS485 Poll:
//   STX GRP ID POLL ETX
//    02  nn nn  C0  03
// Reply:
//   STX GRP ID REP PWRH PWRL ETX
//    02  nn nn  C1  xx   xx   03


void chroma_set_power(int power_level);


//~ int uart_chroma_filestream = -1;
//~ int uart_rs485_filestream = -1;
int chroma_power = 0;
pthread_t chroma_thread;
int switch_poll_period = SWITCH_POLLING_PERIOD;

// power reported by polled nodes.  -1 means no reply. 4095W max.
int node_power[256];


void handler_rec_chroma(char* packet, int size) 
{
	//~ struct rpi_t data;
	int i;
	char msgs[200] = {'\0'};
	char msg[5];
	for(i=0; i<size; i++){
		sprintf(msg, "%02X ", packet[i] & 0xff);
		strcat(msgs, msg);
	}
	log_info("CHROMA: Received %s", msgs);
	//~ data.group = packet[2] & 0xff;
	//~ data.node = packet[1] & 0xff;
	//~ data.type = packet[4] & 0xff;
	//~ data.data = ((packet[5] << 8) | (packet[6] & 0xff)) & 0xffff;
}



// RS485 Node Polling -------------------------------------------------



// Poll a switch node for power level
void switch_poll(int group, int node)
{
	int length = 0;
	char poll_buffer[10];

	poll_buffer[length++]=(char)(group & 0x00ff);
	poll_buffer[length++]=(char)(node  & 0x00ff);
	poll_buffer[length++]=PWR_POLL;

	// clear the incoming buffer
	tcflush(uart_rs485_filestream, TCIFLUSH);
	gpioWrite(GPIO_485_DIR, 1);	
	serial_send_485(uart_rs485_filestream, poll_buffer, length);
	// wait for tx
//	tcdrain(uart_rs485_filestream);
	gpioWrite(GPIO_485_DIR, 0);	
}


// Parse the incoming data - extract power level
void switch_reply_parse(char* rec_buffer, int length, int group, int node)
{
	int group_id = -1;
	int node_id = -1;
	int packet_type = -1;
	int power = -1;
	
	if(length == 5){
		group_id    = rec_buffer[0];
		node_id     = rec_buffer[1];
		packet_type = rec_buffer[2];
		power = 256*(int)rec_buffer[3] + (int)rec_buffer[4];
//		log_info("Found node:%d|%d Power:%d", group_id, node_id, power, node, packet_type);
		printf("%d ", node_id);
		if((node_id==node)&&(group_id==group)&&(packet_type==PWR_REPLY)&&(power<=4095)){
			node_power[node_id] = power;
		}
	}
	else{
		// no reply - assume node not connected
		node_power[node] = -1;
	}
}


// Poll all nodes in group, collect power replies
void* chroma_switch_poll(void* argument) 
{
//  struct rpi_t p;
//	int poll_period;
	char reply_buffer[100];
	int polled_group = 0;
	int polled_node = 0;
	int length = 0;
	int total_power;
  
//	poll_period = *((int*)argument);

	while(1){
		for(polled_node = 0; polled_node<16; polled_node++){
			switch_poll(0,polled_node);
			// wait for reply from polled node (blocking)
			serial_packet_wait(uart_rs485_filestream, reply_buffer, &length);	
			switch_reply_parse(reply_buffer, length, polled_group, polled_node);  
			usleep(1000);
		}
		total_power = 0;
		for(polled_node = 0; polled_node<16; polled_node++){
			if(node_power[polled_node] > 0){
				total_power += node_power[polled_node];
//				printf("Node:%d Power:%d",polled_node, node_power[polled_node]);
			}
		}
//		log_info("Total Power:%d", total_power);
		printf(" | Power:%d\n", total_power);
		chroma_set_power(total_power);
	}
	return NULL;
}



// Chroma load control ------------------------------------------------


void chroma_send(char* tx_buffer)
{
	int length = 0;
	
	length = strlen(tx_buffer);
	int count = write(uart_chroma_filestream, &tx_buffer[0], length);	//Filestream, bytes to write, number of bytes to write
	if (count < 0)
	{
		printf("Chroma TX error\n");
	}
}


void chroma_set_mode(int mode)
{
	char tx_buffer[20];
	//~ int length=0;
	
	switch(mode){
		case CHROMA_CURR:
			sprintf(tx_buffer, "MODE CURR\r\n");
			break;
		case CHROMA_POW:
			sprintf(tx_buffer, "MODE POW\r\n");
			break;
		case CHROMA_VOLT:
			sprintf(tx_buffer, "MODE VOLT\r\n");
			break;
		case CHROMA_RES:
			sprintf(tx_buffer, "MODE RES\r\n");
			break;
		}
		
	chroma_send(tx_buffer);
}


void chroma_set_power(int power_level)
{
	char tx_buffer[20];
	//~ int length=0;
	
	if(power_level < 0)
		return;
	if(power_level > 4500)
		return;
	
	sprintf(tx_buffer, "POW %d\r\n", power_level);
	chroma_send(tx_buffer);
}


void chroma_load_on(void)
{
	char tx_buffer[20];
	//~ int length=0;
	
	sprintf(tx_buffer, "LOAD ON\r\n");
	chroma_send(tx_buffer);
}


void chroma_load_off(void)
{
	char tx_buffer[20];
	//~ int length=0;
	
	sprintf(tx_buffer, "LOAD OFF\r\n");
	chroma_send(tx_buffer);
}


void chroma_protect_set(void)
{
	char tx_buffer[20];
	//~ int length=0;
	
	sprintf(tx_buffer, "\r\n");
	chroma_send(tx_buffer);
}


// Initialise Chroma control ------------------------------------------
// Open serial ports for Chroma and RS485 to nodes
// Create node polling thread

void chroma_init(char* tty485, char* tty232)
{
	char dev232[15]="/dev/ttyUSB0";
	char dev485[15]="/dev/ttyAMA0";

	sprintf(dev232, "/dev/%s", tty232);
	sprintf(dev485, "/dev/%s", tty485);

	// initialise the reported power array
	for(int i=0; i<256; i++)
		node_power[i]=-1;
		
	uart_chroma_filestream = tty_open(dev232);
	uart_rs485_filestream  = tty_open(dev485);

	pthread_create(&chroma_thread, NULL, chroma_switch_poll, &switch_poll_period);

	chroma_set_mode(CHROMA_POW);
	chroma_set_power(chroma_power);
	chroma_load_on();
		
//	tty_close(uart_chroma_filestream);
//	tty_close(uart_rs485_filestream);
}


void chroma_close(void)
{
	tty_close(uart_rs485_filestream);
	tty_close(uart_chroma_filestream);
}

