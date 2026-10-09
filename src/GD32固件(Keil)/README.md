# GD32F407 下位机固件（Keil MDK 工程）

垃圾分类识别与自动分拣系统 —— 下位机固件，主控 **GD32F407VE**（ARM Cortex-M4F，168MHz），
基于 GigaDevice GD32F4xx 标准外设库开发。**工程已在 Keil MDK（ARMCC V5.06）实测编译通过：
0 Error、0 Warning，输出 `Project/Objects/GarbageSort.hex`。**

## 一、目录结构

```
GD32固件(Keil)/
├─ Project/
│  ├─ GarbageSort.uvprojx   ← Keil 工程，双击打开
│  ├─ GarbageSort.uvoptx    ← 调试/下载配置
│  └─ Objects/GarbageSort.hex  ← 已编译固件(可直接烧录)
├─ USER/                    主程序、中断、SysTick、RTE_Components.h
├─ BSP/
│  ├─ usart/   usart.c/h    通信协议(USART5 PA11/PA12, AA55 状态机+环形缓冲)
│  ├─ duoji/   SteerGear.c/h  舵机 PWM(TIMER4_CH1 / PA1)
│  ├─ led/     SW2812.c/h   SK6812 软件时序驱动(PD15)
│  ├─ beep/    beep.c/h     蜂鸣器(PC12)
│  ├─ bh1750/  bh1750.c/h + my_iic.c/h  光照传感器(软件I2C PA6/PA7)
│  └─ timer/   timer.c/h    补光灯 PWM(TIMER1_CH0 / PA0, 1kHz)
└─ Firmware/                GD32F4xx CMSIS + 标准外设库(随工程附带，无需另找)
```

## 二、硬件接线（与套件丝印一致）

| 外设 | 引脚 | 配置 |
|---|---|---|
| SG90 舵机 | **PA1** | TIMER4_CH1, AF2, 20ms 周期；比较值 5/10/15/20 = 0°/45°/90°/135° |
| SK6812 全彩灯 | **PD15** | 推挽 GPIO，BOP/BC 位操作软件模拟 GRB 归零码 |
| 有源蜂鸣器 | **PC12** | 高电平有效，分类成功短鸣 120ms |
| BH1750 | **PA6=SCL / PA7=SDA** | 软件 I2C，8 位写地址 0x46，一次性高分辨率模式 |
| 补光灯 | **PA0** | TIMER1_CH0, AF1, 1kHz，占空比 0~1000 |
| 通信串口 | **PA11=TX / PA12=RX** | USART5, AF8, 115200, 8N1 |

## 三、编译与烧录

1. 双击 `Project/GarbageSort.uvprojx`（需安装 Keil MDK-ARM 与 GD32F4xx DFP，
   本工程基于 DFP 3.2.0；`USER/RTE_Components.h` 已静态提供，打开即可编译，无需手动 Manage RTE）
2. `F7`（Build）编译，`F8` 下载；或命令行：`UV4.exe -b GarbageSort.uvprojx`
3. 烧录器按板子实际连接选择（DAP-Link / J-Link / 串口 ISP 均可）

## 四、通信协议（与 PC 端 `core/protocol.py` 一致）

```
帧: AA 55 | CMD | LEN | DATA(n) | SUM | 0D 0A      SUM = CMD ^ LEN ^ DATA[0..n-1]
```

| CMD | 方向 | DATA | 说明 |
|---|---|---|---|
| 0x01 | PC→MCU | `[class]` | 分拣：0 可回收 / 1 厨余 / 2 有害 / 3 其他 |
| 0x02 | PC→MCU | `[duty]` | 补光占空比 0~100（收到后转手动模式） |
| 0x03 | PC→MCU | 空 | 查询一次光照 |
| 0x04 | MCU→PC | `[lux_H, lux_L]` | 光照周期上报（约 1s） |
| 0x05 | MCU→PC | `[ack_cmd, status]` | 应答：status 0=OK 1=ERR |

下位机行为：收到 0x01 → 舵机转档 + 分类颜色灯（蓝/绿/红/黄）+ 蜂鸣 + 回 ACK；
未收到上位机补光指令时，下位机按相同的光照-占空比分段策略自主补光。
接收采用环形缓冲 + 逐字节状态机，校验失败/乱码自动重同步，不丢帧、不卡死。

## 五、无硬件联调

不接板子也可验证上位机全链路：安装 com0com 虚拟串口对，PC 端运行
`PC端上位机(Python)/demo/sim_device.py --port COMx` 模拟下位机。
