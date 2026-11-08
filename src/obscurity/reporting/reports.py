from __future__ import annotations

import json
from pathlib import Path
from obscurity.domain.models import AnalysisSession


def render_markdown(session: AnalysisSession) -> str:
    source = session.source
    lines = ["# Obscurity Investigation Report", "", f"- **Source:** `{source.name}`", f"- **Path:** `{source.path}`", f"- **SHA-256:** `{source.sha256}`", f"- **MD5:** `{source.md5}`", f"- **SHA-1:** `{source.sha1}`", f"- **Format:** {source.properties.format} ({source.properties.mime_type})", f"- **Dimensions:** {source.properties.width} x {source.properties.height}", "", "## Findings", ""]
    if not session.findings:
        lines.append("No findings were recorded.")
    for finding in session.findings:
        lines.extend([f"### {finding.title}", f"- **Severity:** {finding.severity.value}", f"- **Category:** {finding.category}", f"- **Method:** {finding.method or 'internal analysis'}", "", finding.description, "", f"Evidence: `{json.dumps(finding.evidence, sort_keys=True)}`", ""])
    lines.extend(["## Metadata", "", "| Group | Key | Value |", "|---|---|---|"])
    lines.extend(f"| {item.group} | {item.key} | {item.value.replace('|', '\\|')} |" for item in session.metadata)
    lines.extend(["", "## Strings", "", "| Offset | Encoding | Kind | Value |", "|---:|---|---|---|"])
    lines.extend(f"| {item['offset']} | {item['encoding']} | {item['kind']} | {str(item['value']).replace('|', '\\|')} |" for item in session.strings)
    return "\n".join(lines) + "\n"


def export_session(session: AnalysisSession, directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    markdown, session_json = directory / "report.md", directory / "analysis.json"
    return _write_exports(session, markdown, session_json)


def export_session_to_path(session: AnalysisSession, report_path: Path) -> tuple[Path, Path]:
    report_path = report_path.with_suffix(".md")
    session_json = report_path.with_suffix(".json")
    return _write_exports(session, report_path, session_json)


def _write_exports(session: AnalysisSession, markdown: Path, session_json: Path) -> tuple[Path, Path]:
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render_markdown(session), encoding="utf-8")
    session_json.write_text(json.dumps(session.to_dict(), indent=2, default=str), encoding="utf-8")
    return markdown, session_json
