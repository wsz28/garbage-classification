# 四类垃圾 YOLOv8 训练流程（本项目实际使用）

## 1. 真实数据集来源

- 数据集：`yx666-ez/Garbage_classification_Yolov5`（GitHub 开源，YOLO 标注，四大类）
  https://github.com/yx666-ez/Garbage_classification_Yolov5
- 有效数据：`datasets/wangy/` 下 **300 张真实拍摄图片、362 个检测框**，
  内容含塑料瓶/易拉罐/纸箱（可回收物）、剩饭果皮菜叶（厨余垃圾）、
  干电池/过期药品（有害垃圾）、陶瓷碎片/烟头/快餐盒（其他垃圾）等真实生活场景。
- 原始类别 ID：`0 可回收物 / 1 有害垃圾 / 2 厨余垃圾 / 3 其他垃圾`。
  为与下位机分拣协议（舵机角度 0/1/2/3）一致，建集时将标签 **1↔2 互换**，
  最终训练类别为 `0 可回收物 / 1 厨余垃圾 / 2 有害垃圾 / 3 其他垃圾`。
- 划分（固定随机种子 42）：训练集 240 张 / 验证集 60 张，验证集四类框数 23/14/19/18，覆盖均衡。

> 如需进一步提高精度，可按第 5 节自行采集/标注扩充到每类 400 张以上，重训即可。

## 2. 环境（已验证）

```text
Windows 11 + Python 3.13
NVIDIA RTX 4050 6GB, 驱动 610.47
torch 2.11.0+cu126, torchvision 0.26.0+cu126, ultralytics 8.4.99
```

CUDA 版安装（必须 torch 与 torchvision 同为 cu126，否则 NMS 无 CUDA 后端）：

```bash
pip install torch==2.11.0+cu126 torchvision==0.26.0+cu126 ^
  --index-url https://download.pytorch.org/whl/cu126
pip install ultralytics
```

## 3. 训练（实际命令）

```bash
yolo detect train model=yolov8n.pt data=garbage4/data.yaml ^
  epochs=80 imgsz=640 batch=16 device=0 workers=0 ^
  optimizer=SGD lr0=0.01 cos_lr=True mosaic=1.0 mixup=0.1 close_mosaic=10 ^
  degrees=5 scale=0.5 hsv_v=0.4 patience=30 seed=42 amp=True
```

- 基线权重 `yolov8n.pt`（COCO 预训练，nano 版，6.2MB），迁移学习
- 增强：Mosaic 末期关闭、Mixup 0.1、亮度抖动 hsv_v=0.4（兼顾暗光补光场景）、随机缩放/旋转/翻转
- 产物：`runs/garbage4/weights/best.pt`（验证集最优轮次）
- 评估图：`runs/garbage4/results.png`、`confusion_matrix.png`、`val_batch*_pred.jpg`

## 4. 部署

将 `best.pt` 复制到 `PC端上位机(Python)/models/best.pt`，上位机点“加载模型…”
选择该文件即可；推理设备自动选择 GPU（无 CUDA 时回退 CPU）。

## 5. 扩充自己的数据集

1. 手机/摄像头采集四类实物照片（含暗光、多目标、遮挡），用 LabelImg/Roboflow 标注，
   导出 YOLO 格式 `class_id cx cy w h`。
2. 类别 ID 固定为 `0 可回收物 / 1 厨余垃圾 / 2 有害垃圾 / 3 其他垃圾`（与协议一致）。
3. 图片放入 `images/train|val`，标签放入 `labels/train|val`，修改 `data.yaml` 的 path。
4. 显存不足时降 `batch=8` 或 `imgsz=480`；暗光漏检增多时加大 `hsv_v` 并补充暗光样本。
