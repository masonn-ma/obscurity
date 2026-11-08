# Obscurity

Obscurity is a GUI-first image-forensics workbench for triage and investigation of PNG, JPEG, BMP, and GIF files. It preserves the source image, exposes the evidence behind observations, and keeps the analysis engine independent from the Qt presentation layer.

## Requirements

- Python 3.10 or newer
- PySide6, Pillow, and NumPy

Optional integrations are detected at runtime and are never required to launch: `exiftool`, `binwalk`, `zsteg`, `steghide`, `strings`, and `file`.

## Install and run

```text
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
obscurity
```

On Linux/macOS, activate with `source .venv/bin/activate`. The application can also be started with `python -m obscurity.main`.

## Test

```text
pytest
```

Source files are read-only. Derived images, extracted bytes, session JSON, and Markdown reports are written under the selected session workspace. Discovered content is never executed and passphrases are not persisted.
