from enum import Enum


class ExportStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ProcessingJobStatus(str, Enum):
    """v0.2.0 引入；與 ExportStatus 同值不同名以保留語意分離。"""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ColorGradePreset(str, Enum):
    """色調 preset；v0.2.0 起在 ``services.color_grade.apply_grade`` 實作。"""

    SHOWROOM_WHITE = "showroom_white"
    OUTDOOR_WARM = "outdoor_warm"
    NIGHT_COLD = "night_cold"
