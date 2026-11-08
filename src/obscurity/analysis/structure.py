from __future__ import annotations

import struct
from pathlib import Path

from obscurity.domain.models import Finding, Severity, StructureSegment

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SIGNATURES = {b"PK\x03\x04": "ZIP archive", b"%PDF": "PDF document", b"MZ": "PE executable", b"\x7fELF": "ELF executable", b"Rar!\x1a\x07": "RAR archive"}


def _embedded(data: bytes, start: int = 16) -> list[Finding]:
    findings = []
    for signature, name in SIGNATURES.items():
        offset = data.find(signature, start)
        if offset >= 0:
            findings.append(Finding(f"Possible embedded {name}", f"A {name} signature was found at byte offset {offset}.", "structure", Severity.MEDIUM, {"offset": offset, "signature": signature.hex()}, "internal signature scan"))
    return findings


def parse_png(data: bytes) -> tuple[list[StructureSegment], list[Finding]]:
    segments: list[StructureSegment] = []
    findings: list[Finding] = []
    if not data.startswith(PNG_SIGNATURE):
        return segments, [Finding("Invalid PNG signature", "The file does not begin with the PNG signature.", "structure", Severity.HIGH, method="PNG parser")]
    offset = 8
    seen: list[str] = []
    iend_end: int | None = None
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_name = chunk_type.decode("latin1", errors="replace")
        end = offset + 12 + length
        if end > len(data):
            findings.append(Finding("Truncated PNG chunk", f"Chunk {chunk_name} extends beyond the file.", "structure", Severity.HIGH, {"offset": offset, "length": length}, "PNG parser"))
            break
        segments.append(StructureSegment(offset, length, chunk_name, f"PNG {chunk_name} chunk", data={"crc_offset": end - 4}))
        seen.append(chunk_name)
        offset = end
        if chunk_name == "IEND":
            iend_end = end
            break
    if "IHDR" not in seen:
        findings.append(Finding("PNG is missing IHDR", "The required IHDR chunk was not found.", "structure", Severity.HIGH, method="PNG parser"))
    if "IEND" not in seen:
        findings.append(Finding("PNG is missing IEND", "The logical end marker was not found.", "structure", Severity.MEDIUM, method="PNG parser"))
    if iend_end is not None and iend_end < len(data):
        findings.append(Finding("Data after PNG IEND", f"{len(data) - iend_end} bytes follow the PNG end marker.", "structure", Severity.MEDIUM, {"offset": iend_end, "bytes": len(data) - iend_end}, "PNG parser"))
    findings.extend(_embedded(data))
    return segments, findings


def parse_jpeg(data: bytes) -> tuple[list[StructureSegment], list[Finding]]:
    segments: list[StructureSegment] = []
    findings: list[Finding] = []
    if not data.startswith(b"\xff\xd8"):
        return segments, [Finding("Invalid JPEG signature", "The file does not begin with the JPEG SOI marker.", "structure", Severity.HIGH, method="JPEG parser")]
    offset = 2
    eoi_end: int | None = None
    while offset < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker_start = offset
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker == 0xD9:
            segments.append(StructureSegment(marker_start, offset - marker_start, f"FF{marker:02X}", "JPEG end of image"))
            eoi_end = offset
            break
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            segments.append(StructureSegment(marker_start, offset - marker_start, f"FF{marker:02X}", "JPEG marker"))
            continue
        if offset + 2 > len(data):
            findings.append(Finding("Truncated JPEG segment", "A marker does not have a complete length field.", "structure", Severity.HIGH, {"offset": marker_start}, "JPEG parser"))
            break
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        end = offset + length
        if length < 2 or end > len(data):
            findings.append(Finding("Invalid JPEG segment length", f"Marker FF{marker:02X} has an invalid length.", "structure", Severity.HIGH, {"offset": marker_start, "length": length}, "JPEG parser"))
            break
        segments.append(StructureSegment(marker_start, end - marker_start, f"FF{marker:02X}", f"JPEG marker FF{marker:02X}", data={"payload_offset": offset + 2}))
        offset = end
    if eoi_end is not None and eoi_end < len(data):
        findings.append(Finding("Data after JPEG EOI", f"{len(data) - eoi_end} bytes follow the JPEG end marker.", "structure", Severity.MEDIUM, {"offset": eoi_end, "bytes": len(data) - eoi_end}, "JPEG parser"))
    findings.extend(_embedded(data, 2))
    return segments, findings


def parse_structure(path: Path, image_format: str) -> tuple[list[StructureSegment], list[Finding]]:
    data = path.read_bytes()
    if image_format == "PNG":
        return parse_png(data)
    if image_format == "JPEG":
        return parse_jpeg(data)
    return [StructureSegment(0, min(len(data), 64), image_format, f"{image_format} header and boundary information")], _embedded(data, 2)
