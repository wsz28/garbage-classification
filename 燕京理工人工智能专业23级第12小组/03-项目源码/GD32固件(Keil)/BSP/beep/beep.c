#include "beep.h"

void BEEP_Init(void)
{
	rcu_periph_clock_enable(BEEP_RTC);
	
	gpio_mode_set(BEEP_GPIO_Port, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLDOWN, BEEP_Pin);
	
	gpio_output_options_set(BEEP_GPIO_Port, GPIO_OTYPE_PP, GPIO_OSPEED_200MHZ, BEEP_Pin);	
	
	gpio_bit_write(BEEP_GPIO_Port, BEEP_Pin, RESET);
}


void BEEP_Control(char state)
{
	if(state == 1){
		gpio_bit_write(BEEP_GPIO_Port, BEEP_Pin, SET);
	}else{
		gpio_bit_write(BEEP_GPIO_Port, BEEP_Pin, RESET);
	}
}
