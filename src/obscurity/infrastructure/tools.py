from __future__ import annotations

import shutil
import subprocess

OPTIONAL_TOOLS = ("exiftool", "binwalk", "zsteg", "steghide", "strings", "file")


def discover_tools() -> dict[str, dict[str, str | bool]]:
    result: dict[str, dict[str, str | bool]] = {}
    for name in OPTIONAL_TOOLS:
        executable = shutil.which(name)
        entry: dict[str, str | bool] = {"available": executable is not None}
        if executable:
            entry["path"] = executable
            try:
                completed = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=3, check=False)
                output = (completed.stdout or completed.stderr).splitlines()
                if output:
                    entry["version"] = output[0][:200]
            except (OSError, subprocess.SubprocessError) as error:
                entry["error"] = str(error)
        result[name] = entry
    return result
