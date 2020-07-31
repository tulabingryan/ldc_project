#ifndef SWITCH_H
#define SWITCH_H

void handler_rec_switch(char* packet, int size);
//void switch_init(void);
void switch_init(char* tty);
void switch_proc(void);

#endif
