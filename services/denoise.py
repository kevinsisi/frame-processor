"""NAFNet AI 降噪（stub，v0.3.0 才實作）。

實作時參考：
- 模型權重：https://github.com/megvii-research/NAFNet
- GPU runtime：CUDA 12 + PyTorch 2.x；無 GPU 時退回 CPU 並警告處理時間
- 介面預期：``denoise(image: PIL.Image) -> PIL.Image``
"""

from __future__ import annotations


def denoise(*args, **kwargs):
    raise NotImplementedError("denoise.denoise 將在 v0.3.0 實作")
