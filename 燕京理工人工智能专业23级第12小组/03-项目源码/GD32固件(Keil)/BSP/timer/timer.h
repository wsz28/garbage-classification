#ifndef __TIMER_H
#define __TIMER_H

#include "gd32f4xx.h"
#include "stdio.h"
#include "stdlib.h"
#include "string.h"


#define PWM_RTC 				RCU_GPIOA
#define PWM_GPIO_Port		GPIOA
#define PWM_Pin 				GPIO_PIN_0

#define PWM_CHANNEL 		TIMER_CH_0

extern uint16_t TIME_MS;
void pwm_gpio_config(void);
void TIMER1_init(uint16_t arr,uint16_t psc);
void SteerGear_PWM(uint16_t duty);
#endif 

