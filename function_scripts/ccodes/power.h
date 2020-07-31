#ifndef POWER_H
#define POWER_H

#define POWER_REPORTING_PERIOD 2


void handler_rec_power(char* packet, int size);
void power_init(void);

#endif

