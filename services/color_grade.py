"""色調預設（stub，v0.2.0 才實作）。

預期介面：``apply_grade(image, preset: ColorGradePreset) -> PIL.Image``。

v0.2.0 用純 Pillow 實作三組 preset（不需 AI）：

- ``SHOWROOM_WHITE`` — 展示間白：白平衡矯正、輕度提亮、降低色彩飽和度
- ``OUTDOOR_WARM`` — 戶外暖調：暖色偏移、輕微 vibrance、增加對比
- ``NIGHT_COLD`` — 夜拍冷調：冷色偏移、降低噪點、提暗部
"""

from __future__ import annotations


def apply_grade(*args, **kwargs):
    raise NotImplementedError("color_grade.apply_grade 將在 v0.2.0 實作")
