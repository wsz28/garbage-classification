#ifndef __SteerGear_H
#define __SteerGear_H

#include "gd32f4xx.h"

void pwm_init(void);
void pwm_set(uint16_t value);
void SteerGear_DJ(uint16_t mode);

extern uint16_t steer_pwm ;

#endif
