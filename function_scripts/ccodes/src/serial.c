#include <stdio.h>
#include <unistd.h>			//Used for UART
#include <fcntl.h>			//Used for UART
#include <termios.h>			//Used for UART

#include "serial.h"

int uart_chroma_filestream = -1;
int uart_rs485_filestream = -1;


int tty_open(const char* tty)
{
	int filestream = -1;
	
	//-------------------------
	//----- SETUP USART 0 -----
	//-------------------------
	//At bootup, pins 8 and 10 are already set to UART0_TXD, UART0_RXD (ie the alt0 function) respectively
//	int uart0_filestream = -1;
	
	//OPEN THE UART
	//The flags (defined in fcntl.h):
	//	Access modes (use 1 of these):
	//		O_RDONLY - Open for reading only.
	//		O_RDWR - Open for reading and writing.
	//		O_WRONLY - Open for writing only.
	//
	//	O_NDELAY / O_NONBLOCK (same function) - Enables nonblocking mode. When set read requests on the file can return immediately with a failure status
	//											if there is no input immediately available (instead of blocking). Likewise, write requests can also return
	//											immediately with a failure status if the output can't be written immediately.
	//
	//	O_NOCTTY - When set and path identifies a terminal device, open() shall not cause the terminal device to become the controlling terminal for the process.
	filestream = open(tty, O_RDWR | O_NOCTTY );// | O_NDELAY);		//Open in non blocking read/write mode
	if (filestream == -1)
	{
		//ERROR - CAN'T OPEN SERIAL PORT
		printf("Error - Unable to open UART.  Ensure it is not in use by another application\n");
		return filestream;
	}
	
	//CONFIGURE THE UART
	//The flags (defined in /usr/include/termios.h - see http://pubs.opengroup.org/onlinepubs/007908799/xsh/termios.h.html):
	//	Baud rate:- B1200, B2400, B4800, B9600, B19200, B38400, B57600, B115200, B230400, B460800, B500000, B576000, B921600, B1000000, B1152000, B1500000, B2000000, B2500000, B3000000, B3500000, B4000000
	//	CSIZE:- CS5, CS6, CS7, CS8
	//	CLOCAL - Ignore modem status lines
	//	CREAD - Enable receiver
	//	IGNPAR = Ignore characters with parity errors
	//	ICRNL - Map CR to NL on input (Use for ASCII comms where you want to auto correct end of line characters - don't use for bianry comms!)
	//	PARENB - Parity enable
	//	PARODD - Odd parity (else even)
	struct termios options;
	tcgetattr(filestream, &options);
	options.c_cflag = B57600 | CS8 | CLOCAL | CREAD;		//<Set baud rate
	options.c_iflag = IGNPAR;
	options.c_oflag = 0;
	options.c_lflag = 0;
	tcflush(filestream, TCIFLUSH);
	tcsetattr(filestream, TCSANOW, &options);

	return filestream;
}


void tty_close(int filestream)
{
	//----- CLOSE THE UART -----
	close(filestream);
}



void serial_packet_wait(int fd, char* rec_buffer, int* length){
	struct termios options;
	int count = 0;
	char rec_byte;
	int rec_ptr = 0;
	enum {REC_START_WAIT, REC_DATA, REC_DLE, REC_END} rec_state;
	int loop_count = 0;

	tcgetattr(fd, &options);
	options.c_cc[VTIME]=0; 
	options.c_cc[VMIN]=0;
	tcsetattr(fd, TCSANOW, &options);
	
	rec_state = REC_START_WAIT;
	while( (loop_count < 100) && (rec_state != REC_END) && (rec_ptr < 100) ){
		usleep(100);
		loop_count++;
		count = read(fd, &rec_byte, 1);
		if(count != 1)
			continue;
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
				else{
					rec_buffer[rec_ptr++] = rec_byte;
				}
				break;
			case REC_DLE:
				rec_buffer[rec_ptr++] = rec_byte ^ 0x80;
				rec_state = REC_DATA;
				break;
			case REC_END:
				// what are we doing here?
				break;
		}
	}
	if(rec_ptr < 100)
		*length = rec_ptr;
}


int serial_send_485(int fd, char* data, int length)
{
	char data_byte;

	tcdrain(uart_rs485_filestream);
	
	data_byte=STX;
	if(write(fd, &data_byte, 1)<0)
		return -1;
	for(int i=0; i<length; i++){
		if( (data[i]==STX) || (data[i]==ETX) || (data[i]==DLE) ){
			data[i] ^= 0x80;
			data_byte = DLE;
			if(write(fd, &data_byte, 1)<0)
				return -1;
		}
		if(write(fd, &data[i], 1) < 0)
			return -1;	
	}
	data_byte=ETX;
	if(write(fd, &data_byte, 1)<0)
		return -1;

	return 1;
}
