# -*- coding: utf-8 -*-
"""虚拟下位机模拟器 - 无 GD32 硬件时进行 PC 端联调演示

用一对虚拟串口(com0com)或两块 USB-TTL 交叉接线即可:
  PC 上位机 --[虚拟串口对 A]-- sim_device.py --[虚拟串口对 B]-- ...
单机演示: 直接运行, 它会创建两个虚拟串口之一(需安装 com0com),
或者用 --port 参数指定本模拟器打开哪个串口与上位机互通。

功能: 完整实现协议 CMD_SORT/CMD_LIGHT_SET/CMD_LIGHT_QUERY 的应答,
      模拟舵机角度/彩灯颜色/蜂鸣/补光/光照周期上报(可用 --lux 指定固定光照,
      不指定则按正弦波动模拟昼夜光照变化)。
"""
import argparse
import math
import random
import sys
import time
import threading

sys.path.append(__file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])

import serial
from core.protocol import (FrameParser, build_frame, CMD_SORT, CMD_LIGHT_SET,
                           CMD_LIGHT_QUERY, CMD_LIGHT_REPORT, CMD_ACK, CLASSES)

ANGLE = {0: 0, 1: 45, 2: 90, 3: 135}
COLOR = {0: "蓝色", 1: "绿色", 2: "红色", 3: "黄色"}


def main():
    ap = argparse.ArgumentParser(description="GD32 虚拟下位机模拟器")
    ap.add_argument("--port", required=True, help="模拟器串口, 如 COM5")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--lux", type=int, default=None, help="固定光照 lx(默认正弦波动)")
    args = ap.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=0.1)
    print(f"[虚拟下位机] 已打开 {args.port} @ {args.baud}")
    print("[虚拟下位机] 等待上位机指令, Ctrl+C 退出\n")

    state = {"servo": 0, "color": "-", "duty": 0, "counts": [0, 0, 0, 0]}
    lock = threading.Lock()
    parser = FrameParser()
    t0 = time.time()

    def report_loop():
        while True:
            if args.lux is not None:
                lux = args.lux
            else:
                lux = int(200 + 180 * math.sin((time.time() - t0) / 15))
            try:
                ser.write(build_frame(CMD_LIGHT_REPORT,
                                      bytes([(lux >> 8) & 0xFF, lux & 0xFF])))
            except Exception:
                pass
            time.sleep(0.5)

    threading.Thread(target=report_loop, daemon=True).start()

    while True:
        n = ser.in_waiting
        if n == 0:
            time.sleep(0.01)
            continue
        for b in ser.read(n):
            res = parser.feed(b)
            if res is None:
                continue
            cmd, data = res
            if cmd == CMD_SORT and data:
                cls = data[0]
                if cls < 4:
                    with lock:
                        state["servo"] = ANGLE[cls]
                        state["color"] = COLOR[cls]
                        state["counts"][cls] += 1
                    print(f"[分拣] {CLASSES[cls]} -> 舵机 {ANGLE[cls]}° "
                          f"/ 彩灯{COLOR[cls]} / 蜂鸣短鸣")
                    ser.write(build_frame(CMD_ACK, bytes([CMD_SORT, 0x00])))
            elif cmd == CMD_LIGHT_SET and data:
                duty = min(100, data[0])
                with lock:
                    state["duty"] = duty
                print(f"[补光] 占空比 -> {duty}%")
                ser.write(build_frame(CMD_ACK, bytes([CMD_LIGHT_SET, 0x00])))
            elif cmd == CMD_LIGHT_QUERY:
                lux = args.lux or int(200 + 180 * math.sin((time.time() - t0) / 15))
                ser.write(build_frame(CMD_LIGHT_REPORT,
                                      bytes([(lux >> 8) & 0xFF, lux & 0xFF])))


if __name__ == "__main__":
    main()
