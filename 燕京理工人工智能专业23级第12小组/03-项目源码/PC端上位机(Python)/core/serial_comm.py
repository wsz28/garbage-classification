# -*- coding: utf-8 -*-
"""串口收发线程: 独立线程读串口, 通过队列回调 UI; 发送加锁防并发"""
import threading
import time
import queue

import serial
import serial.tools.list_ports

from core.protocol import (FrameParser, build_frame, CMD_SORT, CMD_LIGHT_SET,
                           CMD_LIGHT_QUERY, CMD_LIGHT_REPORT, CMD_ACK)


class SerialComm:
    def __init__(self, on_frame=None, on_status=None):
        """
        on_frame(cmd, data): 收到完整帧回调(UI 线程外, 注意线程安全)
        on_status(text, ok): 连接状态变化回调
        """
        self.ser = None
        self.on_frame = on_frame or (lambda c, d: None)
        self.on_status = on_status or (lambda t, ok: None)
        self._rx_thread = None
        self._running = False
        self._lock = threading.Lock()

    # ---------- 端口扫描 ----------
    @staticmethod
    def list_ports():
        """返回可用串口列表 [(port, desc), ...]"""
        ports = []
        for p in serial.tools.list_ports.comports():
            ports.append((p.device, p.description))
        return ports

    # ---------- 连接管理 ----------
    def open(self, port: str, baudrate: int = 115200) -> bool:
        self.close()
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.1)
        except serial.SerialException as e:
            self.on_status(f"连接失败: {e}", False)
            return False
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()
        self.on_status(f"已连接 {port} @ {baudrate}", True)
        return True

    def close(self):
        self._running = False
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=1.0)
        self._rx_thread = None
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.on_status("未连接", False)

    @property
    def is_open(self):
        return bool(self.ser and self.ser.is_open)

    # ---------- 接收线程 ----------
    def _rx_loop(self):
        parser = FrameParser()
        while self._running and self.ser and self.ser.is_open:
            try:
                n = self.ser.in_waiting
                if n == 0:
                    time.sleep(0.005)
                    continue
                raw = self.ser.read(n)
                for b in raw:
                    result = parser.feed(b)
                    if result is not None:
                        self.on_frame(*result)
            except (serial.SerialException, OSError, TypeError):
                self.on_status("串口异常断开", False)
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                return

    # ---------- 发送 ----------
    def _send(self, frame: bytes):
        if not self.is_open:
            return False
        with self._lock:
            try:
                self.ser.write(frame)
                return True
            except (serial.SerialException, OSError):
                self.on_status("发送失败, 串口已断开", False)
                return False

    def send_sort(self, class_id: int) -> bool:
        """下发分拣指令"""
        return self._send(build_frame(CMD_SORT, bytes([class_id])))

    def send_light(self, duty: int) -> bool:
        """下发补光占空比 0~100"""
        return self._send(build_frame(CMD_LIGHT_SET, bytes([max(0, min(100, duty))])))

    def query_light(self) -> bool:
        return self._send(build_frame(CMD_LIGHT_QUERY, b""))
