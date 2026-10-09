# -*- coding: utf-8 -*-
"""逐步执行 run() 内部每一步, 定位崩溃点"""
import sys, traceback
def _show(msg):
    print(msg, flush=True)

try:
    _show("[1] import app.ui_main")
    from app.ui_main import MainWindow, STYLE
    _show("[2] import ok, now QApplication")
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    _show("[3] QApplication created")
    app.setStyleSheet(STYLE)
    _show("[4] setStyleSheet ok")
    win = MainWindow()
    _show("[5] MainWindow created")
    win.show()
    _show("[6] win.show() ok, entering exec loop (will hang - kill after)")
    sys.exit(app.exec_())
except SystemExit as e:
    _show(f"[EXIT] code={e.code}")
except Exception as e:
    _show(f"[ERR] {type(e).__name__}: {e}")
    _show(traceback.format_exc())
