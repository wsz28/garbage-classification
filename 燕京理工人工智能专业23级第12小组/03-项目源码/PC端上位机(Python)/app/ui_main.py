# -*- coding: utf-8 -*-
"""垃圾分类识别与自动分拣系统 - PC 端上位机主界面 (PyQt5)

布局:
 ┌─────────────────────────────┬───────────────┐
 │                             │  识别结果/置信度 │
 │      摄像头画面(YOLO框)      │  四类垃圾计数   │
 │                             │  光照/补光状态  │
 ├─────────────────────────────┤  串口设置/状态  │
 │  系统日志                    │  控制按钮      │
 └─────────────────────────────┴───────────────┘
"""
import os
import sys
import time
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
                             QPushButton, QLineEdit, QTextEdit, QGridLayout,
                             QFileDialog, QMessageBox, QSlider, QFrame)

sys.path.append(__file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])  # 项目根

from core.serial_comm import SerialComm
from core.protocol import CMD_LIGHT_REPORT, CMD_ACK, CLASSES, CLASS_ACTION
from core.yolo_engine import YoloEngine, CLASS_COLORS_BGR
from core.light_policy import LightPolicy, light_level_text

# 中文字体(OpenCV 原生不支持中文, 用 PIL 绘制)
_FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
_CN_FONT_CACHE = {}


def cn_font(size):
    if size not in _CN_FONT_CACHE:
        try:
            _CN_FONT_CACHE[size] = ImageFont.truetype(_FONT_PATH, size)
        except Exception:
            _CN_FONT_CACHE[size] = ImageFont.load_default()
    return _CN_FONT_CACHE[size]


def put_chinese(frame, text, org, size=24, color=(255, 255, 255)):
    """在 BGR 帧上绘制中文, org 为左上角坐标"""
    pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(pil).text(org, text, font=cn_font(size),
                             fill=(color[2], color[1], color[0]))
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


STYLE = """
QMainWindow { background: #f4f6fa; }
QGroupBox {
    font: 12pt 'Microsoft YaHei'; color: #2c3e50; font-weight: bold;
    border: 1px solid #d0d7e2; border-radius: 8px; margin-top: 12px;
    background: white;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
QLabel { font: 10pt 'Microsoft YaHei'; color: #34495e; }
QComboBox, QLineEdit {
    font: 10pt 'Microsoft YaHei'; border: 1px solid #c3cbd9;
    border-radius: 4px; padding: 4px 6px; background: white;
}
QPushButton {
    font: 10.5pt 'Microsoft YaHei'; padding: 6px 12px; border-radius: 6px;
    border: none; background: #3498db; color: white;
}
QPushButton:hover { background: #2d86c2; }
QPushButton:disabled { background: #b8c4d4; }
QPushButton#btnConnect[connected="true"] { background: #e67e22; }
QTextEdit {
    font: 9pt 'Consolas'; border: 1px solid #d0d7e2; border-radius: 6px;
    background: #1e2630; color: #a8d08d;
}
QSlider::groove:horizontal { height: 6px; background: #c3cbd9; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #3498db; width: 16px; margin: -5px 0; border-radius: 8px;
}
QSlider::handle:horizontal:hover { background: #2d86c2; }
QSlider::sub-page:horizontal { background: #3498db; border-radius: 3px; }
"""

# 四类垃圾颜色图例 (与 draw_boxes 配色一致, 用于右侧面板展示)
CLASS_LEGEND = [
    ("可回收物", "#ff901e"),  # BGR(255,144,30) -> 近似 #ff901e
    ("厨余垃圾", "#3cc83c"),
    ("有害垃圾", "#3c3ce6"),
    ("其他垃圾", "#28c8f0"),
]


class CameraWorker(QThread):
    """摄像头采集 + YOLO 推理线程(推理在子线程, UI 不卡顿)"""
    frame_ready = pyqtSignal(object, list)   # (frame, boxes)
    error = pyqtSignal(str)

    def __init__(self, engine: YoloEngine, cam_id=0, width=1280, height=720):
        super().__init__()
        self.engine = engine
        self.cam_id = cam_id
        self.width, self.height = width, height
        self._run = True
        self.conf = 0.30

    def stop(self):
        self._run = False
        self.wait(2000)

    def run(self):
        cap = cv2.VideoCapture(self.cam_id, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if not cap.isOpened():
            self.error.emit(f"摄像头 {self.cam_id} 打开失败")
            return
        while self._run:
            ok, frame = cap.read()
            if not ok:
                self.error.emit("摄像头读取失败")
                break
            boxes = self.engine.detect(frame, self.conf) if self.engine.ok else []
            self.frame_ready.emit(frame, boxes)
            time.sleep(0.005)
        cap.release()


class DemoWorker(QThread):
    """无摄像头演示模式: 程序生成模拟检测画面, 循环识别四类垃圾。
    输出 (frame, boxes) 与 CameraWorker 完全一致, 后续计数/串口分拣逻辑复用。"""
    frame_ready = pyqtSignal(object, list)

    OBJ_MS, GAP_MS = 3000, 1200      # 每类停留 3s, 空场 1.2s
    FRAME_MS = 50

    def __init__(self, width=1280, height=720):
        super().__init__()
        self.width, self.height = width, height
        self._run = True

    def stop(self):
        self._run = False
        self.wait(2000)

    # ---------- 场景绘制 ----------
    def _background(self, frame, t):
        # 深色渐变背景
        top = np.array([28, 32, 42], dtype=np.uint8)
        bot = np.array([52, 58, 72], dtype=np.uint8)
        grad = np.zeros_like(frame)
        for y in range(frame.shape[0]):
            grad[y, :] = top + (bot - top) * y / frame.shape[0]
        frame[:] = grad
        # 传送带
        cv2.fillPoly(frame, [np.array([[180, 470], [1100, 470], [1220, 700], [60, 700]])],
                     (48, 48, 52))
        for x in range(0, self.width, 90):
            off = int((t * 60) % 90)
            cv2.line(frame, (x + off, 478), (x - 120 + off, 700), (70, 70, 76), 2)
        # 顶部识别区域提示线
        cv2.rectangle(frame, (300, 120), (980, 470), (70, 90, 110), 1)
        return frame

    @staticmethod
    def _draw_bottle(f, cx, cy):
        cv2.rectangle(f, (cx - 34, cy - 70), (cx + 34, cy + 70), (210, 170, 60), -1)
        cv2.rectangle(f, (cx - 18, cy - 100), (cx + 18, cy - 70), (180, 180, 190), -1)
        cv2.rectangle(f, (cx - 34, cy - 40), (cx + 34, cy + 10), (235, 220, 150), -1)
        cv2.putText(f, "PET", (cx - 26, cy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (40, 90, 160), 2)

    @staticmethod
    def _draw_apple(f, cx, cy):
        cv2.circle(f, (cx - 14, cy + 6), 52, (60, 60, 200), -1)
        cv2.circle(f, (cx + 18, cy - 8), 46, (50, 70, 190), -1)
        cv2.line(f, (cx + 4, cy - 52), (cx + 10, cy - 84), (70, 110, 60), 5)
        cv2.ellipse(f, (cx + 26, cy - 78), (20, 9), -30, 0, 360, (90, 160, 80), -1)
        cv2.circle(f, (cx - 26, cy - 16), 12, (120, 120, 235), -1)

    @staticmethod
    def _draw_battery(f, cx, cy):
        cv2.rectangle(f, (cx - 40, cy - 74), (cx + 40, cy + 74), (60, 60, 210), -1)
        cv2.rectangle(f, (cx - 16, cy - 90), (cx + 16, cy - 74), (150, 150, 160), -1)
        cv2.putText(f, "+", (cx - 12, cy - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (255, 255, 255), 3)
        cv2.putText(f, "-", (cx - 8, cy + 56), cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                    (255, 255, 255), 3)

    @staticmethod
    def _draw_tissue(f, cx, cy):
        pts = np.array([[cx - 58, cy + 30], [cx - 40, cy - 60], [cx + 6, cy - 78],
                        [cx + 56, cy - 34], [cx + 40, cy + 62], [cx - 16, cy + 70]])
        cv2.fillPoly(f, [pts], (190, 195, 200))
        cv2.polylines(f, [pts], True, (150, 155, 160), 2)

    def run(self):
        drawers = [self._draw_bottle, self._draw_apple, self._draw_battery, self._draw_tissue]
        t0 = time.time()
        cycle = self.OBJ_MS * 4 + self.GAP_MS * 4
        while self._run:
            t = int((time.time() - t0) * 1000)
            phase = t % cycle
            idx, boxes = -1, []
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            frame = self._background(frame, t / 1000.0)

            seg = self.OBJ_MS + self.GAP_MS
            k = phase // seg
            in_obj = (phase % seg) < self.OBJ_MS
            if in_obj and k < 4:
                idx = k
                local = phase % seg
                appear = min(1.0, local / 350.0)             # 淡入
                cx = self.width // 2 + int(26 * np.sin(t / 260.0))
                cy = 330 + int(8 * np.sin(t / 170.0))
                size = int(150 * (0.85 + 0.15 * appear))
                x1, y1, x2, y2 = cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2
                drawers[idx](frame, cx, cy)
                conf = 0.86 + 0.09 * np.sin(t / 300.0 + idx) ** 2
                boxes = [(idx, CLASSES[idx], float(min(0.97, conf)), (x1, y1, x2, y2))]

            # HUD
            frame = put_chinese(frame, "演示模式（无摄像头 / 无模型，识别结果由模拟程序生成）",
                                (32, 22), 24, (0, 200, 200))
            frame = put_chinese(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                (1020, 24), 22, (170, 180, 195))
            tip = "等待垃圾进入识别区…" if idx < 0 else f"检测到：{CLASSES[idx]}"
            frame = put_chinese(frame, tip, (430, 150), 30,
                                (255, 255, 255) if idx < 0 else CLASS_COLORS_BGR[idx])
            self.frame_ready.emit(frame, boxes)
            self.msleep(self.FRAME_MS)


class ImageWorker(QThread):
    """无摄像头时的真实数据模式: 循环播放本地真实垃圾照片, 由已训练模型真实推理,
    输出 (frame, boxes) 与 CameraWorker 一致, 计数/串口分拣逻辑完全复用。"""
    frame_ready = pyqtSignal(object, list, str)   # (frame, boxes, filename)

    HOLD_MS, FRAME_MS = 2800, 50       # 每张停留 2.8s, 便于观察与触发一次真实分拣下发

    def __init__(self, engine: YoloEngine, paths, width=1280, height=720, conf=0.25):
        super().__init__()
        self.engine, self.paths = engine, paths
        self.width, self.height, self.conf = width, height, conf
        self._run = True

    def stop(self):
        self._run = False
        self.wait(3000)

    def _load(self, path):
        """读图(支持中文路径), 直接传原图给模型(ultralytics 自带 letterbox),
        显示画布等比缩放并加黑边, 框坐标按缩放比映射到画布"""
        data = np.fromfile(path, dtype=np.uint8)
        im = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if im is None:
            print(f"[IMGW] 读图失败: {os.path.basename(path)}", flush=True)
            return None
        h0, w0 = im.shape[:2]
        s = min(self.width / w0, self.height / h0)
        nw, nh = max(1, int(w0 * s)), max(1, int(h0 * s))
        ox, oy = (self.width - nw) // 2, (self.height - nh) // 2

        # 直接对原图推理 (ultralytics 内部会做 letterbox 保持长宽比, 避免手动 resize 失真)
        boxes_src = self.engine.detect(im, self.conf) if self.engine.ok else []
        # 调试输出: 每张图的推理结果
        print(f"[IMGW] {os.path.basename(path)}原图{w0}x{h0} conf={self.conf:.2f} "
              f"检测到{len(boxes_src)}个目标: " +
              " | ".join(f"{n}({cf*100:.0f}%)" for _, n, cf, _ in boxes_src), flush=True)

        # 原图坐标 -> 画布坐标: 先按 s 缩放, 再加黑边偏移
        boxes = [(idx, name, conf,
                  (int(x1 * s + ox), int(y1 * s + oy),
                   int(x2 * s + ox), int(y2 * s + oy)))
                 for idx, name, conf, (x1, y1, x2, y2) in boxes_src]

        # 显示画布 (仅用于显示, 不用于推理)
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        im_disp = cv2.resize(im, (nw, nh))
        canvas[oy:oy + nh, ox:ox + nw] = im_disp
        return canvas, boxes, os.path.basename(path)

    def run(self):
        results = []
        for p in self.paths:
            if not self._run:
                return
            r = self._load(p)
            if r:
                results.append(r)
        if not results:
            return
        i, hold_from = 0, time.time()
        while self._run:
            frame, boxes, name = results[i]
            view = frame.copy()
            view = put_chinese(
                view, f"真实图片检测 · YOLO 真实推理 · 第 {i + 1}/{len(results)} 张 · {name}",
                (24, 16), 22, (0, 220, 120))
            self.frame_ready.emit(view, boxes, name)
            self.msleep(self.FRAME_MS)
            if (time.time() - hold_from) * 1000 >= self.HOLD_MS:
                i = (i + 1) % len(results)
                hold_from = time.time()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("基于GD32+YOLO的垃圾分类识别与自动分拣系统 — 上位机 v1.1")
        self.resize(1280, 800)

        # 状态(模型路径相对本脚本位置, 不受启动 cwd 影响)
        _PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._proj = _PROJ
        self.engine = YoloEngine(os.path.join(_PROJ, "models", "best.pt"))
        self.comm = SerialComm(on_frame=self.on_serial_frame,
                               on_status=self.on_serial_status)
        self.policy = LightPolicy()
        self.counts = [0, 0, 0, 0]
        self.last_class, self.last_send_ts = -1, 0.0
        self.duty_now = None
        self.cam = None
        self.demo = None
        self.imgw = None
        # 可调阈值: 显示阈值(滑块) + 下发阈值(防误识别重复)
        self.conf_display = 0.25   # 显示阈值, 滑块控制
        self.conf_dispatch = 0.40  # 下发分拣的最低置信度
        self.current_filename = ""

        self._build_ui()
        self.refresh_ports()

        # 光照查询定时器(保持链路活跃)
        self.light_timer = QTimer(self)
        self.light_timer.timeout.connect(lambda: self.comm.query_light())
        self.light_timer.start(1000)

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        # ---- 左: 视频区 ----
        left = QVBoxLayout()
        gb_video = QGroupBox("实时检测画面")
        self.label_video = QLabel("等待摄像头启动…")
        self.label_video.setAlignment(Qt.AlignCenter)
        self.label_video.setMinimumSize(820, 460)
        self.label_video.setStyleSheet(
            "background:#111; color:#666; font:14pt 'Microsoft YaHei'; border-radius:8px;")
        v = QVBoxLayout(gb_video)
        v.addWidget(self.label_video)

        # 置信度阈值滑块条 (视频下方)
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("显示置信度阈值"))
        self.slider_conf = QSlider(Qt.Horizontal)
        self.slider_conf.setRange(5, 95)         # 0.05 - 0.95
        self.slider_conf.setValue(int(self.conf_display * 100))
        self.slider_conf.setFixedWidth(220)
        self.lbl_conf_val = QLabel(f"{self.conf_display:.2f}")
        self.lbl_conf_val.setFixedWidth(40)
        self.slider_conf.valueChanged.connect(self.on_conf_slider)
        conf_row.addWidget(self.slider_conf)
        conf_row.addWidget(self.lbl_conf_val)
        conf_row.addStretch(1)
        # 文件名显示
        self.lbl_filename = QLabel("（未启动图片检测）")
        self.lbl_filename.setStyleSheet("color:#7f8c8d;")
        conf_row.addWidget(self.lbl_filename)
        v.addLayout(conf_row)
        left.addWidget(gb_video, stretch=5)

        gb_log = QGroupBox("系统日志")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        lv = QVBoxLayout(gb_log)
        lv.addWidget(self.log)
        left.addWidget(gb_log, stretch=1)

        root.addLayout(left, stretch=7)

        # ---- 右: 状态面板 ----
        right = QVBoxLayout()

        gb_res = QGroupBox("识别结果")
        g = QGridLayout(gb_res)
        self.lbl_class = QLabel("—")
        self.lbl_class.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        self.lbl_class.setAlignment(Qt.AlignCenter)
        self.lbl_conf = QLabel("置信度: --")
        self.lbl_conf.setAlignment(Qt.AlignCenter)
        self.lbl_conf.setFont(QFont("Microsoft YaHei", 11))
        g.addWidget(QLabel("当前类别"), 0, 0)
        g.addWidget(self.lbl_class, 1, 0, 1, 2)
        g.addWidget(self.lbl_conf, 2, 0, 1, 2)
        # 显示本帧检测到的所有目标
        self.lbl_targets = QLabel("本帧目标: --")
        self.lbl_targets.setWordWrap(True)
        self.lbl_targets.setStyleSheet("color:#34495e; font:9pt 'Microsoft YaHei';")
        g.addWidget(self.lbl_targets, 3, 0, 1, 2)
        right.addWidget(gb_res)

        # 类别图例
        gb_legend = QGroupBox("类别图例")
        lv2 = QVBoxLayout(gb_legend)
        for name, hex_color in CLASS_LEGEND:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{hex_color}; font:14pt 'Microsoft YaHei';")
            dot.setFixedWidth(24)
            lab = QLabel(name)
            lab.setStyleSheet("font:10pt 'Microsoft YaHei'; color:#34495e;")
            row.addWidget(dot)
            row.addWidget(lab)
            row.addStretch(1)
            lv2.addLayout(row)
        right.addWidget(gb_legend)

        gb_cnt = QGroupBox("分类计数")
        g = QGridLayout(gb_cnt)
        self.lbl_counts = []
        for i, name in enumerate(CLASSES):
            l1 = QLabel(name)
            l2 = QLabel("0")
            l2.setFont(QFont("Arial", 16, QFont.Bold))
            l2.setAlignment(Qt.AlignCenter)
            l2.setStyleSheet(f"color:{CLASS_LEGEND[i][1]};")
            g.addWidget(l1, i // 2, (i % 2) * 2)
            g.addWidget(l2, i // 2, (i % 2) * 2 + 1)
            self.lbl_counts.append(l2)
        self.lbl_total = QLabel("总计: 0")
        g.addWidget(self.lbl_total, 2, 0, 1, 4)
        right.addWidget(gb_cnt)

        gb_light = QGroupBox("光照环境")
        g = QGridLayout(gb_light)
        self.lbl_lux = QLabel("-- lx")
        self.lbl_lux.setFont(QFont("Arial", 14, QFont.Bold))
        self.lbl_fill = QLabel("光照充足 / 补光关闭")
        self.lbl_fill.setStyleSheet("color:#27ae60; font-weight:bold;")
        g.addWidget(QLabel("BH1750 实测"), 0, 0)
        g.addWidget(self.lbl_lux, 0, 1)
        g.addWidget(QLabel("补光状态"), 1, 0)
        g.addWidget(self.lbl_fill, 1, 1)
        right.addWidget(gb_light)

        gb_serial = QGroupBox("串口设置")
        g = QGridLayout(gb_serial)
        self.cb_port = QComboBox()
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.cb_baud.setCurrentText("115200")
        self.btn_refresh = QPushButton("刷新端口")
        self.btn_connect = QPushButton("连接")
        self.btn_connect.setObjectName("btnConnect")
        self.lbl_status = QLabel("状态: 未连接")
        self.lbl_status.setStyleSheet("color:#c0392b; font-weight:bold;")
        g.addWidget(QLabel("串口"), 0, 0)
        g.addWidget(self.cb_port, 0, 1)
        g.addWidget(QLabel("波特率"), 1, 0)
        g.addWidget(self.cb_baud, 1, 1)
        g.addWidget(self.btn_refresh, 2, 0)
        g.addWidget(self.btn_connect, 2, 1)
        g.addWidget(self.lbl_status, 3, 0, 1, 2)
        right.addWidget(gb_serial)

        gb_ctrl = QGroupBox("控制")
        g = QGridLayout(gb_ctrl)
        self.btn_model = QPushButton("加载模型…")
        self.btn_cam = QPushButton("启动摄像头")
        self.btn_img = QPushButton("图片检测(真实模型)")
        self.btn_demo = QPushButton("演示模式(无摄像头·模拟)")
        self.btn_reset = QPushButton("计数清零")
        self.btn_manual = QPushButton("手动测试分拣")
        self.btn_img.setStyleSheet(
            "QPushButton { background:#27ae60; } QPushButton:hover { background:#1e8449; }")
        self.btn_demo.setStyleSheet(
            "QPushButton { background:#8e44ad; } QPushButton:hover { background:#7d3c98; }")
        g.addWidget(self.btn_model, 0, 0)
        g.addWidget(self.btn_cam, 0, 1)
        g.addWidget(self.btn_img, 1, 0, 1, 2)
        g.addWidget(self.btn_demo, 2, 0, 1, 2)
        g.addWidget(self.btn_reset, 3, 0)
        g.addWidget(self.btn_manual, 3, 1)
        right.addWidget(gb_ctrl)

        right.addStretch(1)
        root.addLayout(right, stretch=3)

        # ---- 信号绑定 ----
        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect.clicked.connect(self.toggle_connect)
        self.btn_model.clicked.connect(self.load_model)
        self.btn_cam.clicked.connect(self.toggle_camera)
        self.btn_img.clicked.connect(self.toggle_image)
        self.btn_demo.clicked.connect(self.toggle_demo)
        self.btn_reset.clicked.connect(self.reset_counts)
        self.btn_manual.clicked.connect(self.manual_sort)

    # ---------------- 工具 ----------------
    def log_msg(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {text}")

    def on_conf_slider(self, val):
        """实时调整显示置信度阈值, 同时更新各 worker 的推理阈值"""
        self.conf_display = val / 100.0
        self.lbl_conf_val.setText(f"{self.conf_display:.2f}")
        if self.imgw:
            self.imgw.conf = self.conf_display
        if self.cam:
            self.cam.conf = self.conf_display
        self.engine.conf = self.conf_display

    # ---------------- 串口 ----------------
    def refresh_ports(self):
        self.cb_port.clear()
        for dev, desc in SerialComm.list_ports():
            self.cb_port.addItem(f"{dev} - {desc}", dev)

    def toggle_connect(self):
        if self.comm.is_open:
            self.comm.close()
            return
        dev = self.cb_port.currentData()
        if not dev:
            QMessageBox.warning(self, "提示", "请先选择串口(可点刷新端口)")
            return
        if self.comm.open(dev, int(self.cb_baud.currentText())):
            self.btn_connect.setText("断开")
            self.btn_connect.setProperty("connected", "true")
        else:
            self.btn_connect.setText("连接")

    def on_serial_status(self, text, ok):
        self.lbl_status.setText(f"状态: {text}")
        self.lbl_status.setStyleSheet(
            "color:#27ae60; font-weight:bold;" if ok else "color:#c0392b; font-weight:bold;")
        if not ok:
            self.btn_connect.setText("连接")

    def on_serial_frame(self, cmd, data):
        if cmd == CMD_LIGHT_REPORT and len(data) >= 2:
            lux = (data[0] << 8) | data[1]
            self.lbl_lux.setText(light_level_text(lux))
            duty = self.policy.update(lux)
            if duty is not None and duty != self.duty_now:
                self.duty_now = duty
                self.comm.send_light(duty)
                self.lbl_fill.setText(f"暗光补光中 ({duty}%)")
                self.lbl_fill.setStyleSheet("color:#e67e22; font-weight:bold;")
                self.log_msg(f"光照 {lux}lx -> 下发补光 {duty}%")
            elif self.duty_now in (None, 0):
                self.lbl_fill.setText("光照充足 / 补光关闭")
                self.lbl_fill.setStyleSheet("color:#27ae60; font-weight:bold;")
        elif cmd == CMD_ACK and len(data) >= 2:
            ack_cmd, st = data[0], data[1]
            name = {0x01: "分拣", 0x02: "补光"}.get(ack_cmd, hex(ack_cmd))
            if st == 0:
                self.log_msg(f"下位机应答: {name}指令执行成功")
            else:
                self.log_msg(f"下位机应答: {name}指令执行失败!")

    # ---------------- 摄像头/YOLO ----------------
    def load_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模型权重", "", "PyTorch (*.pt)")
        if not path:
            return
        eng = YoloEngine(path)
        if eng.ok:
            self.engine = eng
            if self.cam:
                self.cam.engine = eng
            self.log_msg(f"模型加载成功: {path}")
        else:
            QMessageBox.critical(self, "错误", eng.err)

    def toggle_camera(self):
        if self.cam and self.cam.isRunning():
            self.cam.stop()
            self.cam = None
            self.btn_cam.setText("启动摄像头")
            self.label_video.setText("摄像头已停止")
            return
        if (self.demo and self.demo.isRunning()) or (self.imgw and self.imgw.isRunning()):
            QMessageBox.information(self, "提示", "请先停止图片检测 / 演示模式")
            return
        if not self.engine.ok:
            QMessageBox.warning(self, "提示",
                                "未加载模型: 请先加载 models/best.pt\n"
                                "(训练方法见 train/README.md)\n\n"
                                "没有摄像头时可使用绿色按钮“图片检测(真实模型)”")
            return
        self.cam = CameraWorker(self.engine)
        self.cam.frame_ready.connect(self.on_frame)
        self.cam.error.connect(lambda e: self.log_msg("摄像头: " + e))
        self.cam.start()
        self.btn_cam.setText("停止摄像头")

    def toggle_image(self):
        """无摄像头时的真实数据模式: 选择真实垃圾照片文件夹, 模型真实推理并真实下发分拣"""
        if self.imgw and self.imgw.isRunning():
            self.imgw.stop()
            self.imgw = None
            self.btn_img.setText("图片检测(真实模型)")
            self.label_video.setText("图片检测已停止")
            self.lbl_filename.setText("（未启动图片检测）")
            self.log_msg("图片检测已停止")
            return
        if (self.cam and self.cam.isRunning()) or (self.demo and self.demo.isRunning()):
            QMessageBox.information(self, "提示", "请先停止摄像头 / 演示模式")
            return
        if not self.engine.ok:
            QMessageBox.warning(self, "提示",
                                "未加载真实模型: 请先加载 models/best.pt\n(该权重由真实数据集训练, 训练方法见 train/README.md)")
            return
        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        folder = QFileDialog.getExistingDirectory(self, "选择真实垃圾图片文件夹", default_dir)
        if not folder:
            return
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
        paths = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                 if f.lower().endswith(exts)]
        if not paths:
            QMessageBox.warning(self, "提示", "该文件夹下没有图片 (jpg/png/bmp)")
            return
        self.imgw = ImageWorker(self.engine, paths, conf=self.conf_display)
        self.imgw.frame_ready.connect(self.on_img_frame)
        self.imgw.start()
        self.btn_img.setText("停止图片检测")
        self.log_msg(f"图片检测已启动: {len(paths)} 张真实照片, YOLO 真实推理, 阈值={self.conf_display:.2f}"
                     + ("，分拣指令将下发到下位机" if self.comm.is_open else "（串口未连接，仅界面计数）"))

    def toggle_demo(self):
        """无摄像头/无模型演示: 模拟识别画面, 仍通过串口真实下发分拣指令"""
        if self.demo and self.demo.isRunning():
            self.demo.stop()
            self.demo = None
            self.btn_demo.setText("演示模式(无摄像头·模拟)")
            self.label_video.setText("演示已停止")
            self.log_msg("演示模式已停止")
            return
        if (self.cam and self.cam.isRunning()) or (self.imgw and self.imgw.isRunning()):
            QMessageBox.information(self, "提示", "请先停止摄像头 / 图片检测")
            return
        self.demo = DemoWorker()
        self.demo.frame_ready.connect(self.on_frame)
        self.demo.start()
        self.btn_demo.setText("停止模拟演示")
        self.log_msg("演示模式已启动: 模拟四类垃圾循环识别（非真实模型数据, 仅用于流程演示）"
                     + ("，分拣指令将下发到下位机" if self.comm.is_open else "（串口未连接，仅界面演示）"))

    def on_img_frame(self, frame, boxes, filename):
        """ImageWorker 信号: 额外带文件名, 更新顶部文件名标签后走统一流程"""
        self.current_filename = filename
        self.lbl_filename.setText(f"当前文件: {filename}")
        self.on_frame(frame, boxes)

    def on_frame(self, frame, boxes):
        frame = self.draw_boxes(frame, boxes)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_BGR888)
        self.label_video.setPixmap(QPixmap.fromImage(img).scaled(
            self.label_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.handle_detection(boxes)

    @staticmethod
    def draw_boxes(frame, boxes):
        for idx, name, conf, (x1, y1, x2, y2) in boxes:
            c = CLASS_COLORS_BGR[idx]
            cv2.rectangle(frame, (x1, y1), (x2, y2), c, 3)
            tag = f"{name} {conf*100:.1f}%"
            # 标签背景宽度按字数估算 (中文 = 2 个 ascii 宽度)
            tag_w = 20 * len(tag) // 2 + 12
            cv2.rectangle(frame, (x1, y1 - 38), (x1 + tag_w, y1), c, -1)
            put_chinese(frame, tag, (x1 + 4, y1 - 34), 26, (255, 255, 255))
        return frame

    def handle_detection(self, boxes):
        # 显示本帧所有检测目标
        if boxes:
            tgt = " · ".join(f"{n}({cf*100:.0f}%)" for _, n, cf, _ in
                             sorted(boxes, key=lambda b: -b[2]))
            self.lbl_targets.setText(f"本帧目标 ({len(boxes)}): {tgt}")
        else:
            self.lbl_targets.setText("本帧目标: 无")

        best = YoloEngine.pick_best(boxes)
        if best is None:
            self.lbl_class.setText("—")
            self.lbl_class.setStyleSheet("color:#7f8c8d;")
            self.lbl_conf.setText("置信度: --")
            return
        idx, name, conf, _ = best
        self.lbl_class.setText(name)
        color = {0: "#ff901e", 1: "#3cc83c", 2: "#3c3ce6", 3: "#28c8f0"}[idx]
        self.lbl_class.setStyleSheet(f"color:{color};")
        self.lbl_conf.setText(f"置信度: {conf*100:.1f}%")

        # 防重复下发: 同类别 2s 冷却, 置信度达标才下发
        now = time.time()
        if conf >= self.conf_dispatch and not (idx == self.last_class and now - self.last_send_ts < 2.0):
            self.last_class, self.last_send_ts = idx, now
            self.counts[idx] += 1
            self.lbl_counts[idx].setText(str(self.counts[idx]))
            self.lbl_total.setText(f"总计: {sum(self.counts)}")
            if self.comm.is_open:
                self.comm.send_sort(idx)
                self.log_msg(f"识别[{name}] {conf*100:.1f}% -> 下发分拣指令({idx})")
            else:
                self.log_msg(f"识别[{name}] {conf*100:.1f}% (串口未连接, 仅计数)")

    # ---------------- 控制 ----------------
    def reset_counts(self):
        self.counts = [0, 0, 0, 0]
        for i, l in enumerate(self.lbl_counts):
            l.setText("0")
        self.lbl_total.setText("总计: 0")
        self.log_msg("计数已清零")

    def manual_sort(self):
        """手动测试: 按当前识别类别下发, 未识别时循环 0-3 演示"""
        idx = self.last_class if self.last_class >= 0 else 0
        if self.comm.is_open:
            self.comm.send_sort(idx)
            self.log_msg(f"手动测试: 下发分拣指令({CLASSES[idx]})")
        else:
            self.log_msg("串口未连接, 无法下发")

    def closeEvent(self, e):
        if self.cam:
            self.cam.stop()
        if self.imgw:
            self.imgw.stop()
        if self.demo:
            self.demo.stop()
        self.comm.close()
        e.accept()


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
