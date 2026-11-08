from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from PIL import Image

from obscurity.domain.models import ImageProperties, SourceInfo

_FORMAT_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "BMP": "image/bmp", "GIF": "image/gif"}


def identify_image(path: Path) -> ImageProperties:
    with Image.open(path) as image:
        image_format = (image.format or "UNKNOWN").upper()
        return ImageProperties(
            format=image_format,
            mime_type=_FORMAT_MIME.get(image_format, mimetypes.guess_type(path.name)[0] or "application/octet-stream"),
            width=image.width,
            height=image.height,
            mode=image.mode,
            frame_count=getattr(image, "n_frames", 1),
            bits_per_pixel=len(image.getbands()) * 8,
        )


def calculate_hashes(path: Path) -> dict[str, str]:
    digests = {name: hashlib.new(name) for name in ("sha256", "md5", "sha1")}
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            for digest in digests.values():
                digest.update(chunk)
    return {name: digest.hexdigest() for name, digest in digests.items()}


def inspect_source(path: Path) -> SourceInfo:
    properties = identify_image(path)
    hashes = calculate_hashes(path)
    stat = path.stat()
    return SourceInfo(str(path.resolve()), path.name, stat.st_size, __import__("datetime").datetime.fromtimestamp(stat.st_mtime).isoformat(), hashes["sha256"], hashes["md5"], hashes["sha1"], properties)
