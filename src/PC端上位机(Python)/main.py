# -*- coding: utf-8 -*-
"""基于GD32+YOLO的垃圾分类识别与自动分拣系统 - PC 端上位机入口

用法:
    python main.py              # 启动上位机(需先在 models/ 放入 best.pt)
    python demo/sim_device.py   # (可选)另一个终端运行虚拟下位机, 无硬件演示联调
"""
import sys


def _bootstrap():
    # stdout/stderr 强制无缓冲, 便于定位启动阶段问题
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    print("[main] booting...", flush=True)
    from app.ui_main import run
    print("[main] ui_main imported, calling run()", flush=True)
    run()


if __name__ == "__main__":
    _bootstrap()
