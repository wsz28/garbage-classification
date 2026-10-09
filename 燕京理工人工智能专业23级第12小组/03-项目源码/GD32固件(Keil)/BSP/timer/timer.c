#include "timer.h"

uint16_t TIME_MS = 0;


void pwm_gpio_config(void)
{
    rcu_periph_clock_enable(PWM_RTC);
    
    gpio_mode_set(PWM_GPIO_Port, GPIO_MODE_AF, GPIO_PUPD_NONE, PWM_Pin);
    gpio_output_options_set(PWM_GPIO_Port, GPIO_OTYPE_PP, GPIO_OSPEED_50MHZ, PWM_Pin);

    gpio_af_set(PWM_GPIO_Port, GPIO_AF_1, PWM_Pin);
}


void TIMER1_init(uint16_t arr,uint16_t psc)
{
    timer_oc_parameter_struct timer_ocintpara;
    timer_parameter_struct timer_initpara;

    rcu_periph_clock_enable(RCU_TIMER1);				//开启定时器时钟
    rcu_timer_clock_prescaler_config(RCU_TIMER_PSC_MUL4);		//因为APB1是AHB的4分频，因此定时器时钟CK_TIMERx = CK_AHB = 200m

    timer_deinit(TIMER1);												//复位定时器

    /* TIMER1 configuration */
    timer_initpara.prescaler         = psc;		//预分频
		timer_initpara.period            = arr;		//计数值
    timer_initpara.alignedmode       = TIMER_COUNTER_EDGE;
    timer_initpara.counterdirection  = TIMER_COUNTER_UP;
    timer_initpara.clockdivision     = TIMER_CKDIV_DIV1;
    timer_initpara.repetitioncounter = 0;
    timer_init(TIMER1,&timer_initpara);

    /* CH1,CH2 and CH3 configuration in PWM mode */
    timer_ocintpara.ocpolarity  = TIMER_OC_POLARITY_HIGH;
    timer_ocintpara.outputstate = TIMER_CCX_ENABLE;
    timer_ocintpara.ocnpolarity  = TIMER_OCN_POLARITY_HIGH;
    timer_ocintpara.outputnstate = TIMER_CCXN_DISABLE;
    timer_ocintpara.ocidlestate  = TIMER_OC_IDLE_STATE_LOW;
    timer_ocintpara.ocnidlestate = TIMER_OCN_IDLE_STATE_LOW;

    timer_channel_output_config(TIMER1,PWM_CHANNEL,&timer_ocintpara);
//    timer_channel_output_config(TIMER1,TIMER_CH_2,&timer_ocintpara);
//    timer_channel_output_config(TIMER1,TIMER_CH_3,&timer_ocintpara);

    /* CH0 configuration in PWM mode1,duty cycle 0% */
    timer_channel_output_pulse_value_config(TIMER1,PWM_CHANNEL,500);
    timer_channel_output_mode_config(TIMER1,PWM_CHANNEL,TIMER_OC_MODE_PWM0);
    timer_channel_output_shadow_config(TIMER1,PWM_CHANNEL,TIMER_OC_SHADOW_DISABLE);


    /* auto-reload preload enable */
    timer_auto_reload_shadow_enable(TIMER1);
    /* auto-reload preload enable */
    timer_enable(TIMER1);								//使能定时器
}

/**************************************************************
*功  能：	调节PWM
*参  数：	无
*返回值：	无 
**************************************************************/
void SteerGear_PWM(uint16_t duty)
{
	if(duty > 1000)
	{
		duty = 1000;
	}
	timer_channel_output_pulse_value_config(TIMER1,PWM_CHANNEL,duty);
}	
