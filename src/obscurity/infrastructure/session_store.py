from __future__ import annotations

import json
import uuid
from pathlib import Path
from obscurity.domain.models import AnalysisSession, session_directory


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (Path.home() / ".obscurity" / "sessions")

    def create(self, source: Path, session: AnalysisSession) -> Path:
        directory = session_directory(self.root, source, session.session_id)
        for name in ("artifacts/visual", "artifacts/extracted", "artifacts/strings", "artifacts/tool-output", "logs"):
            (directory / name).mkdir(parents=True, exist_ok=True)
        self.save(directory, session)
        return directory

    def save(self, directory: Path, session: AnalysisSession) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "session.json").write_text(json.dumps(session.to_dict(), indent=2, default=str), encoding="utf-8")

    def new_id(self) -> str:
        return uuid.uuid4().hex[:12]
