/*!
    \file    main.c
    \brief   基于 GD32F407 + YOLO 的垃圾分类识别与自动分拣系统 —— 下位机主程序

    硬件连接(嵌入式系统基础开发套件 GD32F407VE):
        舵机(投料挡板) : PA1  TIMER4_CH1  AF2   200Hz PWM, pulse 5/10/15/20 = 0/45/90/135 度
        SK6812 状态灯 : PD15 软件时序(GRB 24bit, 单灯)
        蜂鸣器        : PC12 高电平有效
        BH1750 光照   : PA6=SCL / PA7=SDA 软件I2C, 地址0x46
        补光灯 PWM    : PA0  TIMER1_CH0  AF1   1kHz, 占空比 0~1000 (对应0~100%)
        通信串口      : USART5 PA11=TX / PA12=RX AF8  115200 8N1

    通信协议(与 PC 端 core/protocol.py 完全一致):
        AA 55 | CMD | LEN | DATA(n) | SUM | 0D 0A
        0x01 分拣 DATA=[class(0~3)]
        0x02 补光设置 DATA=[duty%(0~100)]
        0x03 查询光照 DATA=[]
        0x04 光照上报 DATA=[lux_H,lux_L] (MCU->PC)
        0x05 应答 DATA=[ack_cmd,status]  (MCU->PC)
*/

#include "gd32f4xx.h"
#include "systick.h"
#include <stdio.h>

#include "SW2812.h"
#include "beep.h"
#include "SteerGear.h"
#include "timer.h"
#include "bh1750.h"
#include "usart.h"

/* 类别 -> SK6812 颜色 (0xRRGGBB, 与PC端 CLASS_ACTION 颜色一致) */
static const uint32_t CLASS_COLOR[4] = {
    0x1E90FFu,  /* 可回收物 - 蓝 */
    0x3CC83Cu,  /* 厨余垃圾 - 绿 */
    0xE63C3Cu,  /* 有害垃圾 - 红 */
    0xF0C828u   /* 其他垃圾 - 黄 */
};

#define BEEP_TIME_MS        120u    /* 分拣提示音时长 */

static volatile uint32_t tick_20ms = 0;    /* 由主循环累加 */
static volatile uint16_t beep_left  = 0;   /* 蜂鸣器剩余鸣响时间(单位20ms) */
static volatile uint8_t  auto_light = 1;   /* 1=本地自动补光; 收到0x02后转手动 */
static uint16_t lux_now = 0xFFFF;

/* 补光灯: 输入百分比0~100, TIMER1 比较值范围0~1000 */
static void light_set_percent(uint8_t percent)
{
    if (percent > 100) percent = 100;
    SteerGear_PWM((uint16_t)percent * 10u);
}

/* 本地补光保底策略(与 PC 端 light_policy.duty_from_lux 完全相同),
   仅在未连接/未收到上位机补光指令时自主运行 */
static uint8_t duty_from_lux_local(uint16_t lux)
{
    if (lux >= 300) return 0;
    if (lux >= 150) return (uint8_t)(60u * (300u - lux) / 150u);
    if (lux >= 80)  return (uint8_t)(90u - 30u * (lux - 80u) / 70u);
    return 100;
}

static void send_light_report(uint16_t lux)
{
    uint8_t d[2];
    d[0] = (uint8_t)(lux >> 8);
    d[1] = (uint8_t)(lux & 0xFF);
    USART_SendFrame(CMD_LIGHT_REPORT, d, 2);
}

static void send_ack(uint8_t ack_cmd, uint8_t status)
{
    uint8_t d[2];
    d[0] = ack_cmd;
    d[1] = status;
    USART_SendFrame(CMD_ACK, d, 2);
}

/* 执行一次分拣动作: 舵机转档 + 分类灯效 + 提示音 */
static void do_sort(uint8_t class_id)
{
    if (class_id > 3) {
        send_ack(CMD_SORT, ACK_ERR);
        return;
    }
    SteerGear_DJ(class_id);                 /* mode 0/1/2/3 -> 0/45/90/135 度 */
    SK6812_Handle(CLASS_COLOR[class_id]);
    BEEP_Control(1);
    beep_left = BEEP_TIME_MS / 20u;
    send_ack(CMD_SORT, ACK_OK);
}

/* 上电自检: 灯四色流动 + 蜂鸣 + 补光闪烁 + 舵机归零 */
static void self_test(void)
{
    uint8_t i;
    for (i = 0; i < 4; i++) {
        SK6812_Handle(CLASS_COLOR[i]);
        BEEP_Control(1);
        delay_1ms(100);
        BEEP_Control(0);
        delay_1ms(100);
    }
    SK6812_Handle(0x000000u);

    SteerGear_DJ(0);
    light_set_percent(50);
    delay_1ms(300);
    light_set_percent(0);
}

int main(void)
{
    uint8_t  cmd, data[FRAME_MAX_DATA], dlen;
    uint16_t bh_wait = 0;          /* BH1750 转换等待计数(20ms) */
    uint8_t  bh_busy = 0;          /* 是否已发起一次测量 */

    systick_config();
    BEEP_Init();
    SK6812_Init();
    USART_CommInit();
    pwm_init();                          /* 舵机 TIMER4 / PA1 */
    pwm_gpio_config();                   /* 补光 TIMER1 / PA0 */
    TIMER1_init(1000u - 1u, 200u - 1u);  /* 200MHz/200=1MHz, ARR999 -> 1kHz */
    BH1750_Init();

    self_test();

    while (1) {
        /* ---------- 1. 处理上位机指令 ---------- */
        if (USART_GetFrame(&cmd, data, &dlen)) {
            switch (cmd) {
            case CMD_SORT:
                if (dlen >= 1) do_sort(data[0]);
                else           send_ack(CMD_SORT, ACK_ERR);
                break;
            case CMD_LIGHT_SET:
                if (dlen >= 1) {
                    light_set_percent(data[0]);
                    auto_light = 0;       /* 以上位机策略为准 */
                    send_ack(CMD_LIGHT_SET, ACK_OK);
                } else {
                    send_ack(CMD_LIGHT_SET, ACK_ERR);
                }
                break;
            case CMD_LIGHT_QUERY:
                send_light_report(lux_now);
                break;
            default:
                break;
            }
        }

        /* ---------- 2. 蜂鸣器到时关闭(非阻塞) ---------- */
        if (beep_left > 0) {
            beep_left--;
            if (beep_left == 0) BEEP_Control(0);
        }

        /* ---------- 3. BH1750 光照采集(两阶段, 不阻塞通信) ---------- */
        if (!bh_busy) {
            BH1750_Start();               /* 发起一次高分辨率测量 */
            bh_busy = 1;
            bh_wait = 7;                  /* 7*20ms = 140ms > 120ms 转换时间 */
        } else if (bh_wait > 0) {
            bh_wait--;
            if (bh_wait == 0) {
                lux_now = BH1750_ReadLux();
                bh_busy = 0;
                if (lux_now != 0xFFFF) {
                    send_light_report(lux_now);
                    if (auto_light) {
                        light_set_percent(duty_from_lux_local(lux_now));
                    }
                }
            }
        }

        /* ---------- 4. 20ms 节拍 ---------- */
        delay_1ms(20);
        tick_20ms++;
    }
}
