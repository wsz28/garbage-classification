#ifndef __BH1750_H
#define __BH1750_H

#include "gd32f4xx.h"

/* BH1750 7位地址: 0x23 (ADDR=L)。参考例程使用 0x46, 即 8位写地址(0x23<<1)。
   本驱动与软件I2C例程保持一致, 直接使用 0x46/0x47 */
#define BH1750_ADDR_W   0x46
#define BH1750_ADDR_R   0x47
#define BH1750_PWR_ON   0x01
#define BH1750_RESET    0x07
#define BH1750_ONE_HRES 0x20   /* 一次性高分辨率模式, 测量约120ms */

void     BH1750_Init(void);
void     BH1750_Start(void);
uint16_t BH1750_ReadLux(void);   /* 返回光照强度(lx), 失败返回0xFFFF */

#endif
