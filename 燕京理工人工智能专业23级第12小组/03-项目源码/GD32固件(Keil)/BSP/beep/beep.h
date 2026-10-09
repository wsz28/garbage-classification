#ifndef __BEEP_H__
#define __BEEP_H__

#include "gd32f4xx.h"

#define BEEP_RTC 		RCU_GPIOC
#define BEEP_GPIO_Port	GPIOC
#define BEEP_Pin 		GPIO_PIN_12

void BEEP_Init(void);
void BEEP_Control(char state);


#endif
