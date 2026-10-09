#ifndef __MY_I2C_H__
#define __MY_I2C_H__

#include "gd32f4xx.h"
#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include "gd32f4xx_i2c.h"
#include "systick.h"
                  
#define MY_I2C_SCL_RTC  	RCU_GPIOA
#define MY_I2C_SCL_PORT	GPIOA
#define MY_I2C_SCL_PIN 	GPIO_PIN_6

#define MY_I2C_SDA_RTC  	RCU_GPIOA
#define MY_I2C_SDA_PORT	GPIOA
#define MY_I2C_SDA_PIN	GPIO_PIN_7

#define MY_I2C_SCL_LOW  	(GPIO_BC(MY_I2C_SCL_PORT)  |= MY_I2C_SCL_PIN)									
#define MY_I2C_SCL_HIGH 	(GPIO_BOP(MY_I2C_SCL_PORT) |= MY_I2C_SCL_PIN)
#define MY_I2C_SDA_LOW  	(GPIO_BC(MY_I2C_SDA_PORT)  |= MY_I2C_SDA_PIN)
#define MY_I2C_SDA_HIGH	(GPIO_BOP(MY_I2C_SDA_PORT) |= MY_I2C_SDA_PIN)
#define MY_I2C_SDA_READ	(GPIO_ISTAT(MY_I2C_SDA_PORT) & MY_I2C_SDA_PIN)

//IIC所有操作函数

void MY_IIC_Init(void);                        //初始化IIC的IO口				 
void MY_IIC_Start(void);				        //发送IIC开始信号
void MY_IIC_Stop(void);	  			        //发送IIC停止信号
void MY_IIC_Send_Byte(uint8_t txd);			//IIC发送一个字节
uint8_t MY_IIC_Read_Byte(unsigned char ack);   //IIC读取一个字节
uint8_t MY_IIC_Wait_Ack(void); 				//IIC等待ACK信号
void MY_IIC_Ack(void);					        //IIC发送ACK信号
void MY_IIC_NAck(void);				        //IIC不发送ACK信号
void MY_IIC_Master_Transmit(uint16_t DevAddress, uint8_t *pData, uint16_t Size);
uint8_t MY_IIC_Master_Receive(uint16_t DevAddress, uint8_t *pData, uint16_t Size);	  


#endif 
