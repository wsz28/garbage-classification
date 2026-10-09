# -*- coding: utf-8 -*-
"""YOLOv8 四类垃圾检测模型训练脚本

数据集构建(见 README.md 详细流程):
    datasets/garbage/
        images/train/*.jpg   images/val/*.jpg
        labels/train/*.txt   labels/val/*.txt   (YOLO 格式标注)

训练:  python train.py
评估:  python train.py --mode val
导出:  python train.py --mode export
"""
import argparse

from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="train", choices=["train", "val", "export"])
    ap.add_argument("--data", default="garbage.yaml")
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--weights", default="yolov8n.pt")
    args = ap.parse_args()

    if args.mode == "train":
        # 迁移学习: COCO 预训练权重 -> 四类垃圾
        model = YOLO(args.weights)
        model.train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=30,
            # 数据增强(规模小, 适度增强)
            hsv_h=0.015, hsv_s=0.6, hsv_v=0.5,     # 光照/色度增强, 提升暗光鲁棒性
            degrees=8, translate=0.1, scale=0.5,
            fliplr=0.5, mosaic=1.0, close_mosaic=10,
            project="runs/garbage", name="yolov8n_v1",
        )
    elif args.mode == "val":
        model = YOLO("runs/garbage/yolov8n_v1/weights/best.pt")
        metrics = model.val(data=args.data, imgsz=args.imgsz)
        print("\n===== 验证集指标 =====")
        print(f"mAP50      : {metrics.box.map50:.4f}")
        print(f"mAP50-95   : {metrics.box.map:.4f}")
        print(f"Precision  : {metrics.box.mp:.4f}")
        print(f"Recall     : {metrics.box.mr:.4f}")
    else:
        model = YOLO("runs/garbage/yolov8n_v1/weights/best.pt")
        model.export(format="onnx", imgsz=640)      # 可选导出加速
        print("已导出 onnx, 请将 best.pt 复制到 上位机 models/ 目录")


if __name__ == "__main__":
    main()
