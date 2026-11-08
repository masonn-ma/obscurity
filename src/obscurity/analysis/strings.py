from __future__ import annotations

import re
from pathlib import Path


def extract_strings(data: bytes, minimum: int = 4) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    patterns = [("ascii", re.compile(rb"[\x20-\x7e]{%d,}" % minimum)), ("utf-16-le", re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % minimum)), ("utf-16-be", re.compile(rb"(?:\x00[\x20-\x7e]){%d,}" % minimum))]
    for encoding, pattern in patterns:
        for match in pattern.finditer(data):
            try:
                value = match.group().decode(encoding)
            except UnicodeDecodeError:
                continue
            kind = "text"
            if "://" in value:
                kind = "URL candidate"
            elif re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", value):
                kind = "IP candidate"
            elif re.fullmatch(r"[A-Za-z0-9+/]{8,}={0,2}", value):
                kind = "Base64-like candidate"
            results.append({"offset": match.start(), "length": len(match.group()), "encoding": encoding, "value": value, "kind": kind})
    return sorted(results, key=lambda item: int(item["offset"]))


def extract_file_strings(path: Path, minimum: int = 4) -> list[dict[str, object]]:
    return extract_strings(path.read_bytes(), minimum)
