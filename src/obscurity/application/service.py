from __future__ import annotations

from pathlib import Path

from obscurity.analysis.core import inspect_source
from obscurity.analysis.metadata import read_metadata
from obscurity.analysis.strings import extract_file_strings
from obscurity.analysis.structure import parse_structure
from obscurity.domain.models import AnalysisSession, Finding, Severity, utc_now
from obscurity.infrastructure.session_store import SessionStore
from obscurity.infrastructure.tools import discover_tools


class InvestigationService:
    def __init__(self, store: SessionStore | None = None) -> None:
        self.store = store or SessionStore()
        self.session: AnalysisSession | None = None
        self.directory: Path | None = None

    def open(self, path: Path) -> AnalysisSession:
        source = inspect_source(path)
        self.session = AnalysisSession(self.store.new_id(), utc_now(), source, tool_status=discover_tools())
        self.directory = self.store.create(path, self.session)
        extension = path.suffix.lower().lstrip(".")
        actual = source.properties.format.lower()
        expected = "jpg" if actual == "jpeg" else actual
        if extension and extension != expected:
            self.session.findings.append(Finding("Extension mismatch", f"The filename extension .{extension} differs from detected format {source.properties.format}.", "identification", Severity.MEDIUM, {"extension": extension, "format": actual}, "Pillow content identification"))
        self.store.save(self.directory, self.session)
        return self.session

    def quick_scan(self) -> AnalysisSession:
        session = self._require_session()
        path = Path(session.source.path)
        session.metadata = read_metadata(path)
        session.structure, structure_findings = parse_structure(path, session.source.properties.format)
        session.findings.extend(structure_findings)
        session.strings = extract_file_strings(path)
        if session.strings:
            session.findings.append(Finding("Printable strings found", f"{len(session.strings)} strings were extracted from the source bytes.", "strings", Severity.INFO, {"count": len(session.strings)}, "internal string extractor"))
        session.scan_status = "quick scan complete"
        self._save()
        return session

    def deep_scan(self) -> AnalysisSession:
        session = self.quick_scan()
        session.scan_status = "deep scan complete"
        self._save()
        return session

    def _require_session(self) -> AnalysisSession:
        if self.session is None:
            raise RuntimeError("Open an image before running analysis.")
        return self.session

    def _save(self) -> None:
        if self.session is not None and self.directory is not None:
            self.store.save(self.directory, self.session)
