"""水平校正（stub，v0.5.0 才實作）。

預期介面：``correct_level(image) -> (image, rotation_degrees)``。

實作策略：Hough line 偵測主水平線（地面、車身底盤線、地平線），
旋轉至水平；旋轉量超過閾值（暫定 ±5 度）就視為誤判，回傳 0 不旋轉。
"""

from __future__ import annotations


def correct_level(*args, **kwargs):
    raise NotImplementedError("level_correct.correct_level 將在 v0.5.0 實作")
