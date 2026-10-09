# 垃圾分类识别与自动分拣系统（GD32 + YOLO）

基于 **YOLOv8 深度学习 + GD32 单片机**的垃圾分类识别与自动分拣课程设计项目。摄像头采集画面 → YOLOv8 实时识别四类垃圾（可回收 / 厨余 / 有害 / 其他）→ PC 上位机经串口下发分拣指令 → GD32 驱动舵机 / SK6812 灯带 / 蜂鸣器完成自动分拣，支持 BH1750 光照采集与暗光自适应补光。

## 系统架构

```
┌─────────────┐   USB-TTL 串口   ┌──────────────┐    GPIO   ┌──────────────┐
│  PC 上位机    │ ──────────────→ │   GD32 单片机  │ ────────→ │ 舵机/SK6812  │
│ (PyQt5 + YOLO)│  AA55 协议帧     │ (固件 C/Keil) │           │ 蜂鸣器/补光灯 │
└─────────────┘                 └──────────────┘           └──────────────┘
```

## 目录结构

```
garbage-classification/
├── src/
│   ├── PC端上位机(Python)/      PyQt5 上位机 + YOLOv8 检测（详见其 README）
│   └── GD32固件(Keil)/          GD32 单片机固件（BSP/串口协议/舵机分拣）
├── preview/                     结果预览图（检测示例、混淆矩阵、训练曲线）
└── assets/                      项目资源
```

## 核心模块

| 模块 | 说明 |
|---|---|
| `core/yolo_engine.py` | YOLOv8 推理封装，四类垃圾识别、多目标取最优 |
| `core/protocol.py` | 串口协议帧编解码（AA55\|CMD\|LEN\|DATA\|SUM\|0D0A） |
| `core/serial_comm.py` | 串口收发线程，独立线程防界面卡顿 |
| `core/light_policy.py` | 光照 → 补光 PWM 策略（死区 + 斜坡防抖） |
| `app/ui_main.py` | PyQt5 主界面（检测画面 / 结果 / 计数 / 光照 / 串口 / 日志） |
| `GD32固件` | 舵机分拣、SK6812 分类颜色、蜂鸣器、BH1750 光照采集 |

## 技术栈

- **PC 端**：Python 3.9+ / PyQt5 / YOLOv8 (ultralytics) / pyserial / OpenCV
- **下位机**：GD32F4xx 单片机、Keil、CMSIS 标准外设库
- **通信**：自定义 AA55 串口协议帧（校验和 + 帧头帧尾）

## 运行说明

具体环境安装、运行、无硬件联调方法见源码内各 README：
- PC 上位机：`src/PC端上位机(Python)/README.md`
- 模型训练：`src/PC端上位机(Python)/train/README.md`

> 注：模型权重（`best.pt` / `yolov8*.pt`）、演示视频等大文件未上传，训练方法见 `train/README.md`。
