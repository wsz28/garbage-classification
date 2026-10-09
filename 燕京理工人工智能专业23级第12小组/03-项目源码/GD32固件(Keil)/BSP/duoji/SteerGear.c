#include "SteerGear.h"
#include "stdio.h"


uint16_t steer_pwm = 5;
uint8_t steer_flag=0;
/*******************************************************************
��  �ܣ���� IO��ʼ��
��  ��: ��
����ֵ: ��
********************************************************************/
void pwm_init(void)
{
    /* ʹ�� TIMER4 �� GPIOA ʱ�� */
    rcu_periph_clock_enable(RCU_TIMER4);
    rcu_periph_clock_enable(RCU_GPIOA);

    /* ���� PA1 Ϊ���ù��� TIMER4_CH1 (AF2) */
    gpio_af_set(GPIOA, GPIO_AF_2, GPIO_PIN_1);
    gpio_mode_set(GPIOA, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO_PIN_1);
    gpio_output_options_set(GPIOA, GPIO_OTYPE_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_1);

    /* ��ʱ������ */
    timer_parameter_struct timer_initpara;
    timer_oc_parameter_struct timer_ocintpara;

    timer_deinit(TIMER4);
    timer_struct_para_init(&timer_initpara);

    timer_initpara.prescaler         = 8400-1;
    timer_initpara.alignedmode       = TIMER_COUNTER_EDGE;
    timer_initpara.counterdirection  = TIMER_COUNTER_UP;
    timer_initpara.period            = 200-1;
    timer_initpara.clockdivision     = TIMER_CKDIV_DIV1;
    timer_initpara.repetitioncounter = 0;
    timer_init(TIMER4, &timer_initpara);

    /* ���� PWM ��� */
    timer_channel_output_struct_para_init(&timer_ocintpara);
    timer_ocintpara.outputstate  = TIMER_CCX_ENABLE;
    timer_ocintpara.outputnstate = TIMER_CCXN_DISABLE;
    timer_ocintpara.ocpolarity   = TIMER_OC_POLARITY_HIGH;
    timer_ocintpara.ocnpolarity  = TIMER_OCN_POLARITY_HIGH;
    timer_ocintpara.ocidlestate  = TIMER_OC_IDLE_STATE_LOW;
    timer_ocintpara.ocnidlestate = TIMER_OCN_IDLE_STATE_LOW;
    timer_channel_output_config(TIMER4, TIMER_CH_1, &timer_ocintpara);

    /* ����ռ�ձ� */
    timer_channel_output_pulse_value_config(TIMER4, TIMER_CH_1, 0);
    timer_channel_output_mode_config(TIMER4, TIMER_CH_1, TIMER_OC_MODE_PWM0);
    timer_channel_output_shadow_config(TIMER4, TIMER_CH_1, TIMER_OC_SHADOW_DISABLE);

    /* ������ʱ�� */
    timer_enable(TIMER4);
}

void pwm_set(uint16_t value)
{
    timer_channel_output_pulse_value_config(TIMER4, TIMER_CH_1, value);
}

/**************************************************************
*��  �ܣ�����PWM
*��  ��: �����λ
*����ֵ: ��
**************************************************************/
void SteerGear_DJ(uint16_t mode)
{
    switch(mode)
    {
    case 0:  pwm_set(5);  break;   /* 0.5ms  -> 0 度 */
    case 1:  pwm_set(10); break;   /* 1.0ms  -> 45 度 */
    case 2:  pwm_set(15); break;   /* 1.5ms  -> 90 度 */
    case 3:  pwm_set(20); break;   /* 2.0ms  -> 135 度 */
    case 4:  pwm_set(25); break;   /* 2.5ms  -> 180 度 */
    default: break;
    }
}


