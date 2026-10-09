# -*- coding: utf-8 -*-
"""光照自适应补光策略

依据 BH1750 实测光照 lux 计算 camera 补光灯 PWM 占空比:
    lux >= 300  : 0%    (光照充足, 关闭补光)
    150~300     : 线性衰减 (0% -> 60%)
    80~150      : 60% -> 90%
    < 80        : 100%  (暗光, 全功率补光)
带 5lx 死区与斜坡限幅, 防止占空比抖动频繁下发串口指令。
"""

DARK_TH = 80       # 全功率阈值 lx
LOW_TH = 150       # 强补光阈值 lx
HIGH_TH = 300      # 关闭补光阈值 lx
DEADZONE = 5       # 变化死区 lx
MAX_STEP = 15      # 单次最大变化 %


def duty_from_lux(lux: float) -> int:
    if lux >= HIGH_TH:
        return 0
    if lux >= LOW_TH:
        # 150->300 线性 60%->0%
        return int(60 * (HIGH_TH - lux) / (HIGH_TH - LOW_TH))
    if lux >= DARK_TH:
        # 80->150 线性 90%->60%
        return int(90 - 30 * (lux - DARK_TH) / (LOW_TH - DARK_TH))
    return 100


class LightPolicy:
    def __init__(self):
        self.last_duty = None
        self.last_lux = None

    def update(self, lux: int):
        """输入新光照, 返回需要下发的占空比(不需要变化返回 None)"""
        if lux is None or lux >= 0xFFFF:
            return None
        self.last_lux = lux

        target = duty_from_lux(lux)
        if self.last_duty is not None:
            # 死区: 光照变化不大且目标接近时不动作
            if self.last_lux is not None and abs(target - self.last_duty) <= 2:
                if abs(lux - (self.last_lux or lux)) < DEADZONE:
                    return None
            # 斜坡限幅
            step = max(-MAX_STEP, min(MAX_STEP, target - self.last_duty))
            new_duty = self.last_duty + step
        else:
            new_duty = target

        if new_duty == self.last_duty:
            return None
        self.last_duty = new_duty
        return new_duty

    @staticmethod
    def status_text(duty) -> str:
        if duty is None or duty == 0:
            return "光照充足 / 补光关闭"
        return f"暗光补光中 ({duty}%)"


def light_level_text(lux):
    if lux is None:
        return "-- lx"
    if lux >= 300:
        return f"{lux} lx (充足)"
    if lux >= 150:
        return f"{lux} lx (偏暗)"
    return f"{lux} lx (昏暗)"
