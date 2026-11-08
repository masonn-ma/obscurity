from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image, ImageOps


def load_array(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGBA"))


def derived_views(path: Path, include_bitplanes: bool = True) -> dict[str, Image.Image]:
    with Image.open(path) as image:
        has_alpha = "A" in image.getbands()
    array = load_array(path)
    views = {"red": Image.fromarray(array[:, :, 0], "L"), "green": Image.fromarray(array[:, :, 1], "L"), "blue": Image.fromarray(array[:, :, 2], "L"), "grayscale": Image.fromarray(np.mean(array[:, :, :3], axis=2).astype(np.uint8), "L"), "inversion": ImageOps.invert(Image.fromarray(array[:, :, :3], "RGB"))}
    if has_alpha:
        views["alpha"] = Image.fromarray(array[:, :, 3], "L")
    if include_bitplanes:
        for channel, index in (("r", 0), ("g", 1), ("b", 2)):
            for bit in range(8):
                views[f"{channel}-bit-{bit}"] = Image.fromarray((((array[:, :, index] >> bit) & 1) * 255).astype(np.uint8), "L")
    return views


def histograms(path: Path) -> dict[str, list[int]]:
    array = load_array(path)
    return {channel: np.bincount(array[:, :, index].ravel(), minlength=256).astype(int).tolist() for channel, index in (("red", 0), ("green", 1), ("blue", 2), ("alpha", 3))}
