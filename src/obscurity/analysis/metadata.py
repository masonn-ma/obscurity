from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import ExifTags, Image

from obscurity.domain.models import MetadataItem


def _read_exiftool(path: Path) -> list[MetadataItem] | None:
    executable = shutil.which("exiftool")
    if not executable:
        return None
    try:
        completed = subprocess.run(
            [executable, "-j", "-G1", "-a", "-s", str(path)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
        record = payload[0]
    except (json.JSONDecodeError, IndexError, TypeError):
        return None
    items = []
    for key, value in record.items():
        if key == "SourceFile":
            continue
        group, _, name = key.partition(":")
        group_name = "GPS" if group.upper() == "GPS" or name.lower().startswith("gps") else group or "Other"
        items.append(MetadataItem(name or key, str(value), group_name, raw=str(value)))
    return items


def read_metadata(path: Path) -> list[MetadataItem]:
    exiftool_items = _read_exiftool(path)
    if exiftool_items is not None:
        return exiftool_items

    items: list[MetadataItem] = []
    with Image.open(path) as image:
        items.extend([MetadataItem("Format", image.format or "Unknown", "General"), MetadataItem("Width", str(image.width), "Image"), MetadataItem("Height", str(image.height), "Image"), MetadataItem("Mode", image.mode, "Image"), MetadataItem("Frame count", str(getattr(image, "n_frames", 1)), "Image")])
        for key, value in image.info.items():
            raw = value.hex() if isinstance(value, bytes) else str(value)
            display = f"<{len(value)} bytes> {raw[:80]}" if isinstance(value, bytes) else raw
            items.append(MetadataItem(str(key), display, "Other", raw=raw))
        for tag_id, value in image.getexif().items():
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            items.append(MetadataItem(name, str(value), "GPS" if name == "GPSInfo" else "EXIF", raw=str(value)))
    return items
