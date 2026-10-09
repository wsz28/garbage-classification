# -*- coding: utf-8 -*-
"""串口通信协议定义与帧编解码 (与 GD32 固件 bsp_usart.c 保持一致)

帧格式: AA 55 | CMD(1B) | LEN(1B) | DATA(nB) | SUM(1B) | 0D 0A
SUM = CMD ^ LEN ^ DATA[0..n-1]
"""

HEAD = b"\xAA\x55"
TAIL = b"\x0D\x0A"
MAX_DATA = 16

# CMD 字定义
CMD_SORT = 0x01          # PC->GD32 分拣指令 DATA=[class]
CMD_LIGHT_SET = 0x02     # PC->GD32 补光设置 DATA=[duty]
CMD_LIGHT_QUERY = 0x03   # PC->GD32 查询光照
CMD_LIGHT_REPORT = 0x04  # GD32->PC 光照上报 DATA=[lux_H, lux_L]
CMD_ACK = 0x05           # GD32->PC 状态应答 DATA=[ack_cmd, status]

ACK_OK, ACK_ERR = 0x00, 0x01

# 垃圾类别
CLASSES = ["可回收物", "厨余垃圾", "有害垃圾", "其他垃圾"]
# 类别 -> (舵机角度, SK6812 颜色RGB)
CLASS_ACTION = {
    0: (0, (30, 144, 255)),     # 蓝
    1: (45, (60, 200, 60)),     # 绿
    2: (90, (230, 60, 60)),     # 红
    3: (135, (240, 200, 40)),   # 黄
}


def checksum(cmd: int, data: bytes) -> int:
    s = cmd ^ len(data)
    for b in data:
        s ^= b
    return s & 0xFF


def build_frame(cmd: int, data: bytes = b"") -> bytes:
    """组装完整帧"""
    assert len(data) <= MAX_DATA
    return HEAD + bytes([cmd, len(data)]) + data + bytes([checksum(cmd, data)]) + TAIL


class FrameParser:
    """状态机逐字节解析, 自动重同步(乱码/丢帧不卡死)"""

    ST_H0, ST_H1, ST_CMD, ST_LEN, ST_DATA, ST_SUM, ST_T0, ST_T1 = range(8)

    def __init__(self):
        self.reset()

    def reset(self):
        self.st = self.ST_H0
        self.cmd = 0
        self.len = 0
        self.data = b""
        self.sum = 0

    def feed(self, byte: int):
        """喂入一个字节, 返回 (cmd, data) 或 None"""
        st = self.st
        if st == self.ST_H0:
            if byte == 0xAA:
                self.st = self.ST_H1
        elif st == self.ST_H1:
            self.st = self.ST_CMD if byte == 0x55 else self.ST_H0
        elif st == self.ST_CMD:
            self.cmd, self.sum = byte, byte
            self.data = b""
            self.st = self.ST_LEN
        elif st == self.ST_LEN:
            self.len = byte
            self.sum ^= byte
            self.st = self.ST_DATA if byte <= MAX_DATA else self.ST_H0
        elif st == self.ST_DATA:
            self.data += bytes([byte])
            self.sum ^= byte
            if len(self.data) >= self.len:
                self.st = self.ST_SUM
        elif st == self.ST_SUM:
            self.st = self.ST_T0 if byte == self.sum else self.ST_H0
        elif st == self.ST_T0:
            self.st = self.ST_T1 if byte == 0x0D else self.ST_H0
        elif st == self.ST_T1:
            self.st = self.ST_H0
            if byte == 0x0A:
                result = (self.cmd, self.data)
                self.reset()
                return result
        return None
