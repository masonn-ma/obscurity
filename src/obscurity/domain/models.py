from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Finding:
    title: str
    description: str
    category: str
    severity: Severity = Severity.INFO
    evidence: dict[str, Any] = field(default_factory=dict)
    method: str = ""
    status: str = "candidate"


@dataclass
class ImageProperties:
    format: str
    mime_type: str
    width: int
    height: int
    mode: str
    frame_count: int = 1
    bits_per_pixel: int | None = None


@dataclass
class SourceInfo:
    path: str
    name: str
    size: int
    modified_time: str
    sha256: str
    md5: str
    sha1: str
    properties: ImageProperties


@dataclass
class MetadataItem:
    key: str
    value: str
    group: str = "Other"
    status: str = "present"
    raw: str | None = None


@dataclass
class StructureSegment:
    offset: int
    length: int
    component: str
    description: str
    status: str = "normal"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisSession:
    session_id: str
    created_at: str
    source: SourceInfo
    findings: list[Finding] = field(default_factory=list)
    metadata: list[MetadataItem] = field(default_factory=list)
    structure: list[StructureSegment] = field(default_factory=list)
    strings: list[dict[str, Any]] = field(default_factory=list)
    tool_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    scan_status: str = "loaded"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_directory(root: Path, source: Path, session_id: str) -> Path:
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in source.stem)
    return root / f"{session_id}_{safe_name}"
