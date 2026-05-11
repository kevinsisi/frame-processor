from enum import Enum


class ExportStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ColorGradePreset(str, Enum):
    SHOWROOM_WHITE = "showroom_white"
    OUTDOOR_WARM = "outdoor_warm"
    NIGHT_COLD = "night_cold"


class AspectRatio(str, Enum):
    """Auto-crop 目標比例。`ORIGINAL` 表示不改變原始 aspect。"""

    ORIGINAL = "original"
    RATIO_3_2 = "ratio_3_2"
    RATIO_4_3 = "ratio_4_3"
    RATIO_16_9 = "ratio_16_9"
    RATIO_1_1 = "ratio_1_1"
    RATIO_9_16 = "ratio_9_16"


ASPECT_RATIO_VALUES: dict[AspectRatio, tuple[int, int] | None] = {
    AspectRatio.ORIGINAL: None,
    AspectRatio.RATIO_3_2: (3, 2),
    AspectRatio.RATIO_4_3: (4, 3),
    AspectRatio.RATIO_16_9: (16, 9),
    AspectRatio.RATIO_1_1: (1, 1),
    AspectRatio.RATIO_9_16: (9, 16),
}


class DenoiseStrength(str, Enum):
    """NAFNet 降噪強度。NONE = 跳過 denoise step。"""

    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class CplStrength(str, Enum):
    """CPL Look 反光抑制強度。NONE = 跳過 anti-glare step。"""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChromaCleanStrength(str, Enum):
    """暗部偽色/彩色雜訊修正強度。NONE = 跳過 chroma cleanup step。"""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProcessingJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
