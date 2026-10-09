# -*- coding: utf-8 -*-
"""YOLOv8 推理封装: 四类垃圾检测, 类别映射与计数

数据集类别(ID 与训练 data.yaml 一致, 且与下位机分拣映射一致):
    0 recyclable  可回收物
    1 kitchen     厨余垃圾
    2 hazardous   有害垃圾
    3 other       其他垃圾
"""
import numpy as np

try:
    from ultralytics import YOLO
    _HAS_ULTRALYTICS = True
except Exception:
    YOLO = None
    _HAS_ULTRALYTICS = False

try:
    import torch
    # 强制 CPU 推理: 避免 PyQt5 事件循环与 CUDA 运行时在同一进程内偶发栈溢出
    # (STATUS_STACK_OVERFLOW 0xC00000FD / STACK_BUFFER_OVERRUN 0xC0000409)
    # 图片检测每张停留 2.8s, CPU 推理耗时 (~1s/张) 完全可接受, 换取稳定性
    _DEVICE = "cpu"
except Exception:
    _DEVICE = "cpu"


CLASS_NAMES_CN = ["可回收物", "厨余垃圾", "有害垃圾", "其他垃圾"]
CLASS_NAMES_EN = ["recyclable", "kitchen", "hazardous", "other"]
CLASS_COLORS_BGR = [(255, 144, 30), (60, 200, 60), (60, 60, 230), (40, 200, 240)]


class YoloEngine:
    def __init__(self, model_path: str, conf: float = 0.45):
        """
        model_path: best.pt(自训练四类模型) 或 yolov8n.pt(预训练, 仅演示流程)
        conf: 置信度阈值
        """
        self.model = None
        self.conf = conf
        self.ok = False
        self.err = ""
        if not _HAS_ULTRALYTICS:
            self.err = "未安装 ultralytics (pip install ultralytics)"
            return
        try:
            self.model = YOLO(model_path)
            self.ok = True
        except Exception as e:
            self.err = f"模型加载失败: {e}"

    def detect(self, frame_bgr: np.ndarray, conf: float = None):
        """返回 [(cls_id, cls_name_cn, conf, (x1,y1,x2,y2)), ...]"""
        if not self.ok or frame_bgr is None:
            return []
        results = self.model.predict(frame_bgr, conf=conf or self.conf,
                                     verbose=False, device=_DEVICE)
        boxes = []
        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls.item())
                # 自训练模型 ID 0-3 直接映射; 预训练 COCO 模型按名字软映射
                if cls_id < len(CLASS_NAMES_CN):
                    idx = cls_id
                else:
                    name = r.names.get(cls_id, "")
                    idx = CLASS_NAMES_EN.index(name) if name in CLASS_NAMES_EN else None
                if idx is None:
                    continue
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                boxes.append((idx, CLASS_NAMES_CN[idx], float(b.conf.item()),
                              (x1, y1, x2, y2)))
        return boxes

    @staticmethod
    def pick_best(boxes):
        """多目标时取置信度最高者下发分拣"""
        if not boxes:
            return None
        return max(boxes, key=lambda b: b[2])
