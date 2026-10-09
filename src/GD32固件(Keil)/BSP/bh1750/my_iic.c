#include "my_iic.h"
 
//MPU IIC 延时函数
void MY_IIC_Delay(void)
{
//	delay_1us(1);
}

//初始化IIC
void MY_IIC_Init(void)
{					     
	rcu_periph_clock_enable(MY_I2C_SCL_RTC);
	rcu_periph_clock_enable(MY_I2C_SDA_RTC);
	
	gpio_mode_set(MY_I2C_SCL_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLUP, MY_I2C_SCL_PIN);
	gpio_output_options_set(MY_I2C_SCL_PORT, GPIO_OTYPE_PP, GPIO_OSPEED_200MHZ, MY_I2C_SCL_PIN);
	gpio_mode_set(MY_I2C_SDA_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLUP, MY_I2C_SDA_PIN);
	gpio_output_options_set(MY_I2C_SDA_PORT, GPIO_OTYPE_PP, GPIO_OSPEED_200MHZ, MY_I2C_SDA_PIN);
	
	//初始上拉，I2C默认空闲状态
	MY_I2C_SCL_HIGH;
	delay_1us(4);
	MY_I2C_SDA_HIGH;
	delay_1us(4);
}


//IO方向设置
void MY_SDA_IN(void)  
{	
	rcu_periph_clock_enable(MY_I2C_SDA_RTC);
	
	gpio_mode_set(MY_I2C_SDA_PORT, GPIO_MODE_INPUT, GPIO_PUPD_PULLUP, MY_I2C_SDA_PIN);
}

void MY_SDA_OUT(void) 
{	
	rcu_periph_clock_enable(MY_I2C_SDA_RTC);
	
	gpio_mode_set(MY_I2C_SDA_PORT, GPIO_MODE_OUTPUT, GPIO_PUPD_PULLUP, MY_I2C_SDA_PIN);
	gpio_output_options_set(MY_I2C_SDA_PORT, GPIO_OTYPE_PP, GPIO_OSPEED_200MHZ, MY_I2C_SDA_PIN);
	
	MY_I2C_SDA_HIGH;
}


//产生IIC起始信号
void MY_IIC_Start(void)
{
	MY_SDA_OUT();		//sda线输出
	MY_I2C_SDA_HIGH;	  
	delay_1us(5);	
	MY_I2C_SCL_HIGH;
	delay_1us(5);	
//	IIC_Delay();
 	MY_I2C_SDA_LOW;	//START:when CLK is high,DATA change form high to low 
//	IIC_Delay();
	delay_1us(5);	
	MY_I2C_SCL_LOW;	//钳住I2C总线，准备发送或接收数据 
}	  
//产生IIC停止信号
void MY_IIC_Stop(void)
{
	MY_SDA_OUT();		//sda线输出
	MY_I2C_SCL_LOW;
	MY_I2C_SDA_LOW;	//STOP:when CLK is high DATA change form low to high
	delay_1us(5);	
// 	IIC_Delay();
	MY_I2C_SCL_HIGH; 
	MY_I2C_SDA_HIGH;	//发送I2C总线结束信号
	delay_1us(5);	
//	IIC_Delay();							   	
}
//等待应答信号到来
//返回值：1，接收应答失败
//        0，接收应答成功
uint8_t MY_IIC_Wait_Ack(void)
{
	uint16_t ucErrTime=0;
	MY_SDA_IN();		//SDA设置为输入  
	MY_I2C_SDA_HIGH;delay_1us(1);	   
	MY_I2C_SCL_HIGH;delay_1us(1);	 
	while(MY_I2C_SDA_READ)
	{
		ucErrTime++;
		if(ucErrTime>250)
		{
			MY_IIC_Stop();
			return 1;
		}
	}
	MY_I2C_SCL_LOW;		//时钟输出0 	   
	return 0;  
} 
//产生ACK应答
void MY_IIC_Ack(void)
{
	MY_I2C_SCL_LOW;
	MY_SDA_OUT();
	MY_I2C_SDA_LOW;
	delay_1us(2);	
//	IIC_Delay();
	MY_I2C_SCL_HIGH;
//	IIC_Delay();
	delay_1us(5);	
	MY_I2C_SCL_LOW;
}
//不产生ACK应答		    
void MY_IIC_NAck(void)
{
	MY_I2C_SCL_LOW;
	MY_SDA_OUT();
	MY_I2C_SDA_HIGH;
	delay_1us(2);	
//	IIC_Delay();
	MY_I2C_SCL_HIGH;
//	IIC_Delay();
	delay_1us(5);	
	MY_I2C_SCL_LOW;
}					 				     
//IIC发送一个字节
//返回从机有无应答
//1，有应答
//0，无应答			  
void MY_IIC_Send_Byte(uint8_t txd)
{                        
    uint8_t t;   
		MY_SDA_OUT(); 	    
    MY_I2C_SCL_LOW;//拉低时钟开始数据传输
    for(t=0;t<8;t++)
    {              	
		if((txd&0x80)>>7){
			MY_I2C_SDA_HIGH;
		}else{
			MY_I2C_SDA_LOW;
		}
		txd<<=1; 	
		delay_1us(2);	
		MY_I2C_SCL_HIGH;
		delay_1us(2);
		MY_I2C_SCL_LOW;	
		delay_1us(2);	
    }	 
} 	    
//读1个字节，ack=1时，发送ACK，ack=0，发送nACK   
uint8_t MY_IIC_Read_Byte(unsigned char ack)
{
	unsigned char i,receive=0;
	MY_SDA_IN();//SDA设置为输入
	for(i=0;i<8;i++ )
	{
		MY_I2C_SCL_LOW; 
		delay_1us(2);	
		MY_I2C_SCL_HIGH;
		receive<<=1;
		if(MY_I2C_SDA_READ)receive++;   
		delay_1us(1);	
		}					 
    if (!ack)
        MY_IIC_NAck();//发送nACK
    else
        MY_IIC_Ack(); //发送ACK   
    return receive;
}
void MY_IIC_Master_Transmit(uint16_t DevAddress, uint8_t *pData, uint16_t Size)
{
    MY_IIC_Start(); // 发送开始信号
    MY_IIC_Send_Byte((uint8_t)(DevAddress << 1) | 0); // 发送设备地址加写操作位
    MY_IIC_Wait_Ack(); // 等待应答
    while (Size--) // 发送数据
    {
        MY_IIC_Send_Byte(*pData++); // 发送一个字节
        MY_IIC_Wait_Ack(); // 等待应答
    }
    MY_IIC_Stop(); // 发送停止信号
}

uint8_t MY_IIC_Master_Receive(uint16_t DevAddress, uint8_t *pData, uint16_t Size)
{
    MY_IIC_Start(); // 发送开始信号
    MY_IIC_Send_Byte((uint8_t)(DevAddress << 1) | 1); // 发送设备地址加读操作位
    if (MY_IIC_Wait_Ack()) // 等待应答
    {
        MY_IIC_Stop(); // 如果没有应答，则发送停止信号并退出
        return 1; // 表示失败
    }
    while (Size)
    {
        if (Size == 1)
        {
            *pData = MY_IIC_Read_Byte(0); // 读取最后一个字节，发送非应答信号
        }
        else
        {
            *pData = MY_IIC_Read_Byte(1); // 读取字节，发送应答信号
        }
        pData++;
        Size--;
    }
    MY_IIC_Stop(); // 发送停止信号
	
    return 0; // 表示成功
}

