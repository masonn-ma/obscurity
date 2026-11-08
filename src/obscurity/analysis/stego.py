from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image


def extract_lsb(path: Path, channels: str = "RGB", bit: int = 0) -> bytes:
    if not 0 <= bit <= 7:
        raise ValueError("bit must be between 0 and 7")
    with Image.open(path) as image:
        array = np.array(image.convert("RGBA"))
    indexes = {"R": 0, "G": 1, "B": 2, "A": 3}
    selected = [indexes[c] for c in channels.upper() if c in indexes]
    if not selected:
        raise ValueError("at least one channel is required")
    bits = ((array[:, :, selected] >> bit) & 1).reshape(-1)
    usable = len(bits) - len(bits) % 8
    return np.packbits(bits[:usable], bitorder="big").tobytes()
