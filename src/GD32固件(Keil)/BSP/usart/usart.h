#ifndef __BSP_USART_H
#define __BSP_USART_H

#include "gd32f4xx.h"
#include "stdio.h"

/* 通信串口: USART5  TX=PA11(AF8)  RX=PA12(AF8)  115200 8N1 */
#define COMM_USART              USART5
#define COMM_USART_RCU          RCU_USART5
#define COMM_GPIO_RCU           RCU_GPIOA
#define COMM_GPIO_PORT          GPIOA
#define COMM_TX_PIN             GPIO_PIN_11
#define COMM_RX_PIN             GPIO_PIN_12
#define COMM_GPIO_AF            GPIO_AF_8
#define COMM_BAUDRATE           115200U

/* ===== 通信协议 (与PC端 core/protocol.py 一致) =====
   帧: AA 55 | CMD | LEN | DATA(n) | SUM | 0D 0A
   SUM = CMD ^ LEN ^ DATA[0..n-1]
*/
#define FRAME_HEAD0             0xAA
#define FRAME_HEAD1             0x55
#define FRAME_TAIL0             0x0D
#define FRAME_TAIL1             0x0A
#define FRAME_MAX_DATA          16

#define CMD_SORT                0x01   /* PC->MCU 分拣指令 DATA=[class] */
#define CMD_LIGHT_SET           0x02   /* PC->MCU 设置补光 DATA=[duty] */
#define CMD_LIGHT_QUERY         0x03   /* PC->MCU 查询光照 DATA=[] */
#define CMD_LIGHT_REPORT        0x04   /* MCU->PC 光照上报 DATA=[lux_H,lux_L] */
#define CMD_ACK                 0x05   /* MCU->PC 应答 DATA=[ack_cmd,status] */

#define ACK_OK                  0x00
#define ACK_ERR                 0x01

void     USART_CommInit(void);
void     USART_SendFrame(uint8_t cmd, const uint8_t *data, uint8_t len);

/* 在main循环中轮询: 收到完整帧时返回1, 并通过指针输出cmd/data/len */
uint8_t  USART_GetFrame(uint8_t *cmd, uint8_t *data, uint8_t *len);

#endif
