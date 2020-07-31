#ifndef CHROMA_H
#define CHROMA_H

// Chroma Defines
#define CHROMA_CURR 0
#define CHROMA_POW  1
#define CHROMA_VOLT 2
#define CHROMA_RES  3

#define SWITCH_POLLING_PERIOD 1

void handler_rec_chroma(char* packet, int size);
void chroma_init(char* tty485, char* tty232);
//void chroma_init(void);

#endif
