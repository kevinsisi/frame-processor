from enum import Enum


class ExportStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ColorGradePreset(str, Enum):
    """v0.2.0 將實作此 enum 對應的色調 preset；v0.1 walking skeleton 不使用。"""

    SHOWROOM_WHITE = "showroom_white"
    OUTDOOR_WARM = "outdoor_warm"
    NIGHT_COLD = "night_cold"
