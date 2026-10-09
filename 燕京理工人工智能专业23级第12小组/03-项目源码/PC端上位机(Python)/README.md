# PC 端上位机 — 基于 GD32+YOLO 的垃圾分类识别与自动分拣系统

Python 3.9+ / PyQt5 上位机：YOLOv8 四类垃圾实时检测 → 串口下发分拣指令 → GD32 驱动舵机/SK6812/蜂鸣器 → 界面回显。

## 1. 功能对照任务书

| 任务书要求 | 实现位置 |
|---|---|
| YOLO 识别可回收物/厨余/有害/其他四类 | `core/yolo_engine.py` + `models/best.pt` |
| 识别后串口下发类别指令 | `app/ui_main.py handle_detection()` |
| 舵机 0°/45°/90°/135° 分拣(下位机) | GD32 `bsp_servo.c` + `main.c protocol_dispatch()` |
| SK6812 分类颜色 + 蜂鸣器短鸣(下位机) | GD32 `bsp_sk6812.c` / `bsp_beep.c` |
| 类别、置信度、各类计数显示 | 主界面"识别结果/分类计数"面板 |
| BH1750 光照采集、暗光自适应补光 | GD32 `bsp_bh1750.c` 上报 + PC `core/light_policy.py` 决策 + GD32 `bsp_light.c` 执行 |
| 光照数据与补光状态上屏 | 主界面"光照环境"面板 |

## 2. 环境安装

```bash
cd PC端上位机(Python)
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

## 3. 运行

```bash
# 1) 将训练好的模型放入 models/best.pt (训练方法见 train/README.md)
# 2) USB-TTL 连接 GD32: TX->PA10, RX->PA9, GND 共地
python main.py
# 3) 界面上: 刷新端口 -> 选择串口 -> 115200 -> 连接 -> 启动摄像头
```

**无硬件联调**（虚拟下位机，自动模拟光照波动）：

```bash
# 安装 com0com 虚拟串口对 COM4<->COM5 后:
python demo/sim_device.py --port COM5
python main.py        # 上位机连 COM4
```

## 4. 目录结构

```
PC端上位机(Python)/
├── main.py                 入口
├── app/ui_main.py          PyQt5 主界面(检测画面/结果/计数/光照/串口/日志)
├── core/
│   ├── protocol.py         串口协议帧编解码(AA55|CMD|LEN|DATA|SUM|0D0A)
│   ├── serial_comm.py      串口收发线程(独立线程, 防卡顿)
│   ├── yolo_engine.py      YOLOv8 推理封装(四类映射/多目标取最优)
│   └── light_policy.py     光照->补光PWM策略(死区+斜坡防抖)
├── train/                  数据集构建与训练脚本(README + garbage.yaml)
├── demo/sim_device.py      虚拟下位机模拟器(无硬件演示)
├── models/                 放置 best.pt
└── requirements.txt
```

## 5. 判定与防重复逻辑

- 置信度 ≥ 0.6 才下发分拣指令；
- 同一类别 2s 冷却，避免连续帧重复计数/重复动作；
- 多目标画面取置信度最高目标；
- 串口未连接时仅计数并在日志提示，不阻塞识别。
