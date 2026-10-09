#include "bh1750.h"
#include "my_iic.h"
#include "systick.h"

/* 初始化: 仅初始化软件I2C引脚并上电复位传感器 */
void BH1750_Init(void)
{
    MY_IIC_Init();
    MY_IIC_Start();
    MY_IIC_Send_Byte(BH1750_ADDR_W);
    MY_IIC_Wait_Ack();
    MY_IIC_Send_Byte(BH1750_PWR_ON);
    MY_IIC_Wait_Ack();
    MY_IIC_Stop();
    delay_1ms(5);
}

/* 启动一次高分辨率测量(完成前约120ms) */
void BH1750_Start(void)
{
    MY_IIC_Start();
    MY_IIC_Send_Byte(BH1750_ADDR_W);
    MY_IIC_Wait_Ack();
    MY_IIC_Send_Byte(BH1750_ONE_HRES);
    MY_IIC_Wait_Ack();
    MY_IIC_Stop();
}

/* 读取测量结果并换算为 lx。返回 0xFFFF 表示传感器无应答 */
uint16_t BH1750_ReadLux(void)
{
    uint8_t buf[2] = {0, 0};
    uint16_t raw;

    MY_IIC_Start();
    MY_IIC_Send_Byte(BH1750_ADDR_R);
    if (MY_IIC_Wait_Ack()) {
        MY_IIC_Stop();
        return 0xFFFF;
    }
    buf[0] = MY_IIC_Read_Byte(1);   /* 高字节, ACK */
    buf[1] = MY_IIC_Read_Byte(0);   /* 低字节, NACK */
    MY_IIC_Stop();

    raw = ((uint16_t)buf[0] << 8) | buf[1];
    return (uint16_t)(raw * 10U / 12U);   /* /1.2, 结果为整数 lx */
}
