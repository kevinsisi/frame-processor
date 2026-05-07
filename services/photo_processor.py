"""照片處理 pipeline 主入口（stub，v0.2+ 才實作）。

預期 contract（暫定）::

    process_photo(photo_id, *, denoise=False, level_correct=False,
                  auto_crop=None, color_grade=None) -> ProcessedPhoto

實際 implementation 會把以下子模組串成 pipeline：denoise → level_correct →
auto_crop → color_grade。每個階段獨立 toggle，輸出寫到
``<storage>/projects/<pid>/processed/<photo_id>.<preset>.jpg``。
"""

from __future__ import annotations


def process_photo(*args, **kwargs):
    raise NotImplementedError("photo_processor.process_photo 將在 v0.2.0 實作")
