#ifndef SERIAL_H
#define SERIAL_H

#define STX		   0x02
#define ETX       0x03
#define PWR_POLL  0xC0
#define PWR_REPLY 0xC1
#define DLE		   0x7c

extern int uart_chroma_filestream;
extern int uart_rs485_filestream;

int tty_open(const char* tty);
void tty_close(int filestream);
void serial_packet_wait(int fd, char* rec_buffer, int* length);
int serial_send_485(int fd, char* data, int length);

#endif

