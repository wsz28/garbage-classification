#ifndef __SW2812_H
#define __SW2812_H
#include "gd32f4xx.h"
#define SK6812_PORT_RTC		RCU_GPIOD
#define SK6812_PORT				GPIOD
#define SK6812_PORT_PIN		GPIO_PIN_15
void SK6812_Init(void);
void SK6812_Set_1(void);
void SK6812_Set_0(void);
void SK6812_Reset(void);
void SK6812_Handle(uint32_t G8R8B8);
#endif

