# Obscurity — GUI Build Plan

**Project name:** Obscurity (`obscurity`)

**Document purpose:** Product and technical implementation plan for an AI coding agent or developer building the first usable GUI version. This document is the source of truth for the initial scope, application behaviour, architecture, and acceptance criteria.

**Product direction:** Build a desktop GUI first. A CLI-only interface may be added later, but it must call the same analysis engine and must not require a second implementation of the forensic logic.

**Primary use case:** Quickly triage and investigate image files encountered during digital-forensics and CTF challenges, without having to open several unrelated tools just to collect basic file information, inspect image structure, view channels and bit planes, extract strings, and test common hiding techniques.

---

## 1. Product objective

Create a desktop application that accepts an image file and provides a consolidated investigation workspace. The application should make the common first steps of image forensics fast and repeatable, while still allowing the user to inspect the evidence behind each result.

The application is an **investigation workbench**, not an automatic "flag finder". It should surface useful observations and possible anomalies, show how each observation was produced, and let the user decide whether it is relevant.

### 1.1 Core outcomes

A user should be able to:

1. Open or drag an image into the application.
2. Immediately identify its actual format, dimensions, size, hashes, and basic properties.
3. Inspect available metadata without manually switching to ExifTool or another utility.
4. Inspect the file's byte-level structure, including format-specific chunks or markers, suspicious trailing bytes, and possible embedded content.
5. Visually inspect RGB channels, alpha, histograms, and individual bit planes.
6. Run common image steganography and embedded-payload checks from one interface.
7. Search printable strings and identify potentially interesting text, URLs, IP addresses, Base64-like content, and configurable CTF flag patterns.
8. Save generated artifacts and export a reproducible investigation report.

### 1.2 Design principles

- **Evidence before conclusions:** show the observation, method, offset or pixel/channel parameters, and relevant output. Do not label an image "stego detected" merely because a heuristic found unusual data.
- **Read-only source handling:** never alter the original input file.
- **Progressive investigation:** make a quick triage useful, then allow the user to run more expensive checks selectively.
- **Visual-first where appropriate:** use the GUI for image transformations, comparisons, and result galleries; use structured tables and hex-oriented views for file structure.
- **Optional integrations:** the application must remain useful when an external utility is not installed.
- **Reproducibility:** record tool availability, versions where possible, settings, timestamps, source hashes, and generated artifact paths.
- **Shared engine:** all forensic operations belong outside the GUI layer so they can later be called by a CLI or another frontend.

---

## 2. Target platform and technology choices

### 2.1 Initial platform

Build a cross-platform desktop application with the following priorities:

1. Linux (Ubuntu/Kali and similar distributions).
2. Windows 10/11, including environments where the user may run the application alongside WSL or security VMs.
3. macOS compatibility where practical, but it is not a release blocker for the first version.

Do not make WSL-specific assumptions. The application should run as a normal desktop process on the host operating system. External tool availability will differ by platform and must be checked at runtime.

### 2.2 Recommended stack

| Area | Choice | Purpose |
|---|---|---|
| Language | Python 3 | Main implementation language |
| GUI | PySide6 (Qt for Python) | Native desktop GUI, layouts, tables, dialogs, graphics, threading/signals |
| Image operations | Pillow | Image loading, conversion, pixel access, thumbnails, channel and bit-plane generation |
| Numerical operations | NumPy | Efficient array operations, histograms, bitwise extraction, entropy calculations |
| Charts | Qt Charts if suitable, otherwise Matplotlib embedded in Qt | Histograms and simple plots |
| CLI output (future) | Rich, optional | Terminal presentation for a later CLI frontend |
| Metadata | ExifTool integration, with Pillow fallback | Broad metadata extraction |
| Embedded data | Binwalk integration, with internal signature scanning fallback | Locate possible embedded files or payloads |
| PNG/BMP stego | zsteg integration where installed, plus native basic LSB extraction | Common CTF checks |
| JPEG/BMP stego | Steghide integration where installed and supported | Password-based embedded-data checks |
| Testing | pytest | Unit and integration tests |
| Packaging | PyInstaller or an equivalent supported packager | Optional desktop distribution after the app works from source |

Use a `pyproject.toml` for project metadata, dependencies, formatting/linting configuration, and test configuration. Pin compatible dependency ranges rather than relying on unbounded latest versions. The implementation agent must verify current package names, supported Python versions, and external-tool command syntax when implementing integrations.

### 2.3 Dependency policy

Separate dependencies into three groups:

**Required Python dependencies**
- `PySide6`
- `Pillow`
- `numpy`

**Useful Python dependencies**
- `matplotlib` or a Qt-native chart package for histogram views.
- `pytest` for tests.
- `pytest-qt` if useful for GUI tests.

**Optional external programs**
- `exiftool`
- `binwalk`
- `zsteg`
- `steghide`
- `strings` / GNU Binutils, where available.
- `file` / libmagic, where available.

The program must check for each optional tool at startup or when its module is opened. Show whether it is available, its detected version when practical, and installation guidance. Missing optional utilities must disable only the functions that depend on them; they must not prevent the application from launching.

Do not silently substitute a different tool or claim that an integration ran when it did not.

---

## 3. Application experience and GUI layout

### 3.1 Overall interface direction

Use a **modern forensic workstation** layout: more approachable than a traditional dense forensic suite, but structured enough for technical investigation. Avoid a generic analytics dashboard full of decorative cards. The primary interface should give the image and its evidence room to be inspected.

Recommended visual direction:
- Dark theme by default, with a light theme considered later.
- Neutral charcoal/slate surfaces and restrained accent colours.
- Clear contrast and readable tables; do not rely on colour alone to indicate severity.
- Compact, consistent spacing and a practical information density.
- Resizable panels and sensible minimum window dimensions.
- No unnecessary animations, gradients, or decorative visual effects.

### 3.2 Main window structure

The main window should contain:

1. **Top application bar**
   - Application name and version.
   - `Open Image` button.
   - `Run Quick Scan` button.
   - `Run Deep Scan` button.
   - Current analysis status/progress indicator.
   - Settings/help menu.

2. **Left navigation sidebar**
   - Overview
   - Metadata
   - File Structure
   - Visual Lab
   - Steganography
   - Strings & Payloads
   - Report

   Each item opens a page in the central workspace. The sidebar should remain visible while an image is loaded.

3. **Central workspace**
   - Displays the selected page.
   - Uses split views where useful (for example, preview beside metadata, hex bytes beside structure rows, source image beside transformed images).
   - Supports tables, image galleries, zooming, and selection details.

4. **Optional findings/inspector panel**
   - A collapsible panel on the right or bottom.
   - Shows the currently selected finding's description, evidence, method, offset/parameters, and artifact path.
   - Do not permanently consume too much space; make it resizable or collapsible.

5. **Bottom status bar**
   - Current source filename.
   - Source hash status / abbreviated SHA-256.
   - Number of findings by severity.
   - Current task state and any non-blocking warnings.

### 3.3 Initial/empty state

When no image is loaded, show a clean welcome page with:
- A large `Open Image` action.
- Drag-and-drop target.
- A short explanation of supported formats.
- A compact list of optional tools and their availability.
- Recent investigations only if a reliable recent-session mechanism is implemented; do not make recent history a blocker for the MVP.

### 3.4 Opening an image

Support:
- File picker.
- Drag-and-drop onto the window.
- Re-opening/replacing the current source.
- Clear error messages for unsupported, unreadable, malformed, or excessively large files.

Initial supported formats should include PNG, JPEG/JPG, BMP, and GIF. Add WebP and TIFF when supported reliably by the installed Pillow build. Identify the real format from file content, not only the filename extension. Display an extension/format mismatch as an observation.

For animated GIFs, identify the frame count and initially show the first frame as the primary preview. Do not silently discard the fact that the image is animated. Frame-by-frame analysis can be a later enhancement.

### 3.5 Analysis workspace navigation

After loading a file, open the Overview page. All pages must operate on the same active source file and analysis session. Replacing the active source must clearly start a new session or ask the user whether to save/export the current session first; do not mix results from different files.

---

## 4. Core user workflows

### Workflow A — Quick triage

1. User opens or drops an image.
2. Application calculates source hashes and identifies the actual file format.
3. Application generates the standard preview and extracts basic metadata.
4. Application performs lightweight structure checks and printable-string extraction.
5. Overview presents the results, warnings, and links to deeper modules.
6. User selects an observation to see the supporting evidence.

The quick scan should finish quickly for normal-sized files and must not run every expensive external utility automatically.

### Workflow B — Deep investigation

1. User selects `Run Deep Scan` or runs selected modules manually.
2. Application runs applicable internal checks and installed optional tools.
3. Each operation reports its status: completed, completed with warnings, skipped, unavailable, failed, or cancelled.
4. Findings are added to the current session with evidence and provenance.
5. User reviews results, opens generated artifacts, and marks findings as interesting, reviewed, or irrelevant.
6. User exports the report and supporting artifacts.

### Workflow C — Visual inspection

1. User opens Visual Lab.
2. The original preview is shown beside a gallery of derived images.
3. User selects RGB, alpha, grayscale, inversion, or a bit plane.
4. The derived image is displayed at a zoomable scale.
5. User can save the currently displayed result as an artifact.
6. The application records the transformation parameters, such as channel and bit position.

### Workflow D — Stego/payload investigation

1. User opens Steganography.
2. The page shows which techniques are applicable to the detected format and which tools are installed.
3. User runs all applicable checks or selects individual techniques.
4. Results are grouped by technique and reported with parameters and extracted output paths.
5. User previews or inspects extracted material without automatically executing it.

### Workflow E — Reporting

1. User opens Report.
2. Application presents a preview of the generated report.
3. User chooses Markdown export (required for MVP) and an output location.
4. Report references the source file, hashes, checks performed, findings, tool availability, and generated artifacts.

---

## 5. Functional module specifications

## 5.1 Overview / Investigation Summary

**Purpose:** Give the user a useful summary immediately after loading a file and after scans complete.

Display:
- Filename and full source path.
- File size in bytes and a readable unit.
- Detected format and filename extension.
- Image width, height, aspect ratio, colour mode, and frame count when applicable.
- SHA-256 hash; MD5 and SHA-1 may also be calculated for compatibility with challenge/platform references.
- Source image preview.
- Quick-scan/deep-scan state and last-run time.
- Counts of findings by severity/category.
- Key observations, for example:
  - Extension does not match detected format.
  - Metadata contains GPS coordinates.
  - Image dimensions or file size are unusual.
  - Bytes occur after the expected end of file marker.
  - Embedded file signatures were found.
  - A steganography tool returned candidate data.

Each observation must link to the relevant module and show why it was raised. A heuristic observation is not proof of malicious content or steganography.

## 5.2 Metadata Inspector

**Purpose:** Collect metadata in one place without requiring the user to manually run several utilities.

Display normalized fields where available:
- File system name, path, size, and timestamps.
- Detected image format and MIME type where known.
- Dimensions, aspect ratio, colour mode, bit depth where it can be established, and frame count.
- EXIF, XMP, IPTC, comments, and format-specific textual metadata.
- Camera make/model, lens, capture date/time, software/processing history, orientation, GPS fields, and other tags when present.
- Compression information where it can be obtained reliably.
- Hashes: SHA-256, MD5, SHA-1.

UI behaviour:
- Use a searchable, sortable key/value table.
- Group fields into General, Image, EXIF, GPS, Software, Dates, and Other where possible.
- Preserve the original tag name and raw value; normalized values must not replace the original value.
- Provide a raw metadata view or expandable details for tool output.
- Provide copy actions for individual values and hashes.
- Clearly distinguish `not present`, `not supported`, and `could not be read`.

Implementation:
- Prefer ExifTool for broad metadata coverage when installed.
- Use Pillow as a built-in fallback for common image properties and metadata.
- Keep tool-specific parsing behind a metadata adapter so the engine returns a consistent data model.

## 5.3 File Structure Analyzer

**Purpose:** Examine how the image is laid out at the byte level and identify data that may not be visible in the normal image preview.

General checks:
- Initial bytes / magic signature.
- Detected format versus file extension.
- File size and expected structure boundaries.
- Expected end marker/footer where the format defines one.
- Data after the expected logical end of the image.
- Known embedded file signatures inside the byte stream.
- Configurable entropy measurements over the file and sliding windows.
- Truncation, malformed segments, unexpected lengths, and parser warnings.

Format-specific MVP parsers:

**PNG**
- Parse the PNG signature.
- Parse chunk boundaries and display chunk type, length, and byte offset.
- Identify `IHDR`, `IDAT`, `IEND`, and other chunks.
- Report missing, duplicated, malformed, or out-of-order critical chunks where the format rules make that conclusion valid.
- Check for bytes after `IEND` and report the exact offset and byte count.
- Surface textual chunks and their values where safely decodable.

**JPEG**
- Parse marker segments and display marker type, length, and offset.
- Show common metadata/application segments such as APP0/APP1/APP13 and comments when present.
- Locate the end-of-image marker and report trailing bytes after it.
- Do not assume every unusual segment is malicious; show the raw marker and parser interpretation.

**BMP and GIF**
- For the MVP, provide reliable header/property inspection and basic boundary checks.
- Deeper format-specific parsing may follow after PNG/JPEG parsing is stable.

UI behaviour:
- Main table columns: offset, component/marker, length, description, status.
- Selecting a row opens the corresponding byte range in a hex view.
- Hex view should show offsets and ASCII interpretation where printable.
- Provide copy offset and copy bytes actions.
- Highlight suspicious observations without colouring the whole row as if it were a confirmed threat.

Implementation:
- Use native Python parsers for the PNG/JPEG functionality required by the MVP.
- Use Binwalk as an optional supplementary signature scan, not as the sole source of truth.
- Keep byte offsets relative to the original file and record them in findings.

## 5.4 Visual Lab

**Purpose:** Make visual transformations and bit-level inspection available in an interactive workspace.

The page should show the original image and a derived-image viewer. Use a thumbnail/gallery area for generated views and a larger viewer for the selected result.

Required transformations:

**Channels**
- Red channel as grayscale intensity.
- Green channel as grayscale intensity.
- Blue channel as grayscale intensity.
- Alpha channel where present; display a clear message when there is no alpha channel.
- Grayscale conversion.
- Inversion/negative.

**Bit planes**
- Extract bit positions 0 through 7 for each RGB channel.
- This results in 24 standard channel/bit-plane views per image.
- Display the selected channel and bit number explicitly.
- Where practical, generate the 24 thumbnails in the background and show them in a gallery.
- Alpha bit planes may be added as an optional extension, not a blocker for the MVP.

**Statistics and inspection**
- Per-channel histograms and overall intensity histogram.
- Basic pixel value inspection on cursor position, showing x/y and RGB(A) values.
- Zoom and pan without changing the underlying source.
- Nearest-neighbour enlargement for inspecting low-resolution pixel patterns.

**Useful later enhancements**
- Brightness and contrast adjustment.
- Side-by-side image comparison and difference image.
- Plane/channel selection presets.
- Batch export of all channel and bit-plane images.

UI requirements:
- Transformations must be non-destructive.
- Clearly label every derived view and its parameters.
- Do not modify or replace the original source image.
- Provide `Save Derived Image` and `Save All Generated Views` actions.
- Large image operations must run outside the UI thread.

Implementation:
- Use Pillow and NumPy for channel and bit-plane calculations.
- Use a Qt graphics/view widget or equivalent for smooth zooming and panning.
- Use a chart library compatible with Qt for histograms.

## 5.5 Steganography Scanner

**Purpose:** Provide a unified interface for common image-steganography checks and simple extraction workflows.

The page must be format-aware. It should list each method, applicability, dependency status, execution status, and result. Do not run an inapplicable tool against a file just to fill the results page.

MVP methods:

1. **Basic LSB extraction**
   - Support common RGB channel extraction for PNG and BMP.
   - Allow channel selection: R, G, B, RGB, and alpha when present.
   - Allow bit position selection from 0 to 7.
   - Record the traversal order and bit packing convention used.
   - Offer text/byte output and image reconstruction where the extracted data can be interpreted as pixels.
   - Make extraction parameters visible and reproducible.

2. **zsteg integration**
   - Use when installed and when the file format is supported by the installed version.
   - Capture standard output, standard error, exit status, and relevant version information.
   - Parse results when practical, but retain raw output for auditability.

3. **Steghide integration**
   - Offer only for supported formats (commonly JPEG and BMP).
   - Do not claim it supports arbitrary formats.
   - Support an optional passphrase supplied interactively by the user.
   - Never store passphrases in the report, application logs, or persistent session data.
   - Do not repeatedly brute-force passwords as part of the MVP.

4. **Embedded payload checks**
   - Use the internal signature scan and optional Binwalk integration.
   - Record signatures, offsets, and extraction status.
   - Extract to the session's artifact directory only after user action or an explicit scan setting.

5. **Strings from source and extracted data**
   - Link to the Strings & Payloads module and allow the user to inspect extracted output.

Results must use cautious language such as `candidate`, `possible embedded data`, or `tool reported a match`. A positive result from a heuristic is not confirmation that a hidden message or flag exists.

UI requirements:
- Show method, format applicability, dependency status, parameters, duration, status, and result summary.
- Allow individual methods to be run independently.
- Provide `Run Applicable Checks`.
- Allow the user to open or save extracted output, but never execute it automatically.
- Store extracted files in a dedicated session subdirectory.

## 5.6 Strings & Payload Inspector

**Purpose:** Find readable or encoded content in the original image and in extracted payloads.

Required extraction:
- ASCII printable strings.
- UTF-8 strings where valid.
- UTF-16 little-endian and big-endian strings.
- Minimum configurable string length (default: 4 characters).
- Source offset for byte-derived strings.

Candidate detection:
- URLs.
- IPv4 addresses (validate candidates rather than accepting any four dotted numbers).
- Email-like strings.
- Base64-like sequences, with an optional safe decode preview.
- Common CTF flag patterns, configurable by the user (examples: `CTF{...}`, `HTB{...}`, `flag{...}`, `RMIT{...}`).
- User-defined regular expressions or simple keyword searches may be added after the basic patterns are stable.

UI behaviour:
- Searchable, filterable results table.
- Columns: text, encoding, source, offset, category, and confidence/status where relevant.
- Selecting a string highlights its offset in the hex view when it came from the original byte stream.
- Show decoded Base64 candidates in a separate preview; do not silently replace the original text.
- Provide copy and export actions.

Do not automatically fetch URLs, connect to IP addresses, or execute decoded content.

## 5.7 Investigation Report Generator

**Purpose:** Produce a clear record of what was examined, what was run, what was found, and where supporting artifacts are stored.

Required output for MVP: Markdown (`.md`). JSON session export is also required for machine-readable results and future CLI reuse.

Report sections:
1. Investigation title and generation timestamp.
2. Source file path, filename, size, detected format, dimensions, and SHA-256.
3. Other hashes where generated.
4. Environment and optional tool availability/version information.
5. Modules and checks executed, skipped, unavailable, failed, or cancelled.
6. Metadata summary.
7. File-structure observations, including offsets and lengths.
8. Visual transformations generated and their parameters.
9. Steganography checks and raw/parsed result summaries.
10. Strings and payload observations.
11. Findings grouped by severity/category.
12. Paths or relative links to saved artifacts.
13. Notes entered by the user.

Report rules:
- Include negative results only when the relevant check actually ran. For example, distinguish `no candidate found by this check` from `check not run` and `tool unavailable`.
- Include relevant evidence and parameters rather than unsupported conclusions.
- Never include a Steghide passphrase or other secret input.
- Use relative artifact paths where possible so an exported investigation folder remains portable.

---

## 6. Findings model and severity language

All modules should create findings through one shared model. Avoid each module inventing its own inconsistent result format.

Recommended finding fields:

| Field | Description |
|---|---|
| `id` | Unique finding identifier within the session |
| `title` | Short, factual label |
| `category` | Metadata, structure, visual, stego, strings, or tool |
| `severity` | Informational, low, medium, high; use sparingly |
| `confidence` | Optional confidence indicator for heuristic/candidate results |
| `description` | What was observed, stated neutrally |
| `evidence` | Supporting values, raw output excerpt, byte range, or artifact reference |
| `method` | Check or technique that generated the finding |
| `parameters` | Relevant settings and options used |
| `source_offset` | Optional byte offset/range in the original file |
| `artifact_paths` | Relative paths to derived or extracted output |
| `status` | New, reviewed, interesting, or dismissed |
| `created_at` | Timestamp |

Severity guidance:
- **Informational:** normal file properties and neutral observations.
- **Low:** an unusual property worth looking at, but with weak implications.
- **Medium:** a concrete anomaly or candidate embedded content requiring investigation.
- **High:** use only when there is strong, directly supported evidence. The tool should rarely assign this automatically.

Do not assign severity based only on a filename, extension, high entropy, or a generic signature match. Explain the evidence behind any non-informational severity.

---

## 7. Analysis modes and task execution

### 7.1 Quick Scan

Quick Scan should run:
- File readability and format identification.
- File size, image dimensions, colour mode, frame count where applicable.
- SHA-256, plus MD5/SHA-1 if included in the same hashing pass.
- Basic metadata extraction.
- Lightweight PNG/JPEG structure checks where supported.
- Basic printable-string extraction.

Quick Scan should not automatically:
- Generate every bit-plane image.
- Run long-running external scans.
- Prompt for passwords.
- Recursively extract nested archives or payloads.

### 7.2 Deep Scan

Deep Scan should run all applicable non-interactive checks:
- Full metadata extraction.
- Format-specific structure parsing.
- Trailing-data and embedded-signature checks.
- Entropy analysis.
- Strings and candidate-pattern detection.
- Installed and applicable steganography utilities that do not require a password.

Do not run password guessing or destructive operations. Visual Lab transformations should be generated on demand, or behind a clearly labelled option if the user asks Deep Scan to generate all standard visual views.

### 7.3 Manual module execution

Every module must also be runnable independently. Re-running one module should update that module's results without deleting findings from unrelated modules. Preserve previous run records or clearly mark superseded results.

### 7.4 Threading and cancellation

- Never run image parsing, hashing, NumPy processing, or external tools on the Qt main/UI thread.
- Use `QThreadPool`/`QRunnable`, `QThread`, or an equivalent Qt worker pattern with signals for progress, results, errors, and completion.
- Provide visible progress for multi-step work.
- Support cancellation for long operations where safe.
- A cancelled task must preserve already completed results and mark unfinished tasks as cancelled.
- Do not update Qt widgets directly from worker threads; communicate through signals/slots.

---

## 8. Architecture and code organisation

Use a layered, modular architecture. The GUI must not contain forensic algorithms, direct subprocess logic, or format parsers.

### 8.1 Architectural layers

**A. Presentation layer — `ui/`**
- PySide6 windows, pages, widgets, dialogs, models, and view controllers.
- Handles user interaction and rendering only.
- Calls application services and displays returned data.

**B. Application layer — `application/`**
- Use cases such as open image, run quick scan, run deep scan, run a module, export report, save artifact, and manage a session.
- Coordinates the relevant analysis modules.
- Owns task orchestration and session-level operations.

**C. Domain layer — `domain/`**
- Shared data models and enums: source file, image properties, metadata item, structure segment, finding, analysis run, artifact, tool status, and session.
- No PySide6 imports and no direct operating-system process calls.

**D. Analysis layer — `analysis/`**
- Format identification, hashing, metadata, structures, visual transformations, strings, stego checks, entropy, signature scanning.
- Each module accepts explicit inputs and returns structured results.
- No UI imports.

**E. Infrastructure layer — `infrastructure/`**
- External-tool adapters and subprocess execution.
- File-system/session storage.
- Configuration and logging.
- Platform-specific tool discovery.

**F. Reporting layer — `reporting/`**
- Markdown report renderer and JSON session serializer.
- Must use the shared session/finding models, not scrape the GUI.

### 8.2 Suggested project structure

The implementation may adjust names, but it should preserve the separation of responsibilities.

```text
obscurity /
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   └── obscurity/
│       ├── __init__.py
│       ├── main.py                 # application entry point
│       ├── bootstrap.py            # dependency wiring and app setup
│       ├── config/
│       │   ├── settings.py
│       │   └── tool_registry.py
│       ├── domain/
│       │   ├── models.py
│       │   ├── enums.py
│       │   └── errors.py
│       ├── application/
│       │   ├── services/
│       │   │   ├── investigation_service.py
│       │   │   ├── scan_service.py
│       │   │   ├── artifact_service.py
│       │   │   └── report_service.py
│       │   └── tasks/
│       │       ├── task_runner.py
│       │       └── workers.py
│       ├── analysis/
│       │   ├── identification.py
│       │   ├── hashing.py
│       │   ├── metadata/
│       │   │   ├── base.py
│       │   │   ├── pillow_reader.py
│       │   │   └── exiftool_reader.py
│       │   ├── structure/
│       │   │   ├── signatures.py
│       │   │   ├── png_parser.py
│       │   │   ├── jpeg_parser.py
│       │   │   ├── bmp_parser.py
│       │   │   └── gif_parser.py
│       │   ├── visual/
│       │   │   ├── channels.py
│       │   │   ├── bitplanes.py
│       │   │   └── histograms.py
│       │   ├── stego/
│       │   │   ├── lsb.py
│       │   │   ├── zsteg_adapter.py
│       │   │   ├── steghide_adapter.py
│       │   │   └── binwalk_adapter.py
│       │   ├── strings/
│       │   │   ├── extractor.py
│       │   │   └── detectors.py
│       │   └── entropy.py
│       ├── infrastructure/
│       │   ├── process_runner.py
│       │   ├── tool_discovery.py
│       │   ├── session_store.py
│       │   ├── file_safety.py
│       │   └── logging.py
│       ├── reporting/
│       │   ├── markdown_report.py
│       │   └── json_export.py
│       └── ui/
│           ├── main_window.py
│           ├── theme/
│           ├── components/
│           ├── pages/
│           │   ├── welcome_page.py
│           │   ├── overview_page.py
│           │   ├── metadata_page.py
│           │   ├── structure_page.py
│           │   ├── visual_lab_page.py
│           │   ├── stego_page.py
│           │   ├── strings_page.py
│           │   └── report_page.py
│           ├── dialogs/
│           └── models/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── gui/
└── docs/
    └── development.md
```

### 8.3 Future CLI compatibility

Do not build the CLI now. However:
- Analysis functions must accept paths/bytes plus explicit options and return domain models or serializable results.
- Application services must not depend on widgets or dialogs.
- Do not put business logic in button callbacks.
- Do not require a Qt application instance to run an analysis module.
- The future CLI should be a thin frontend that calls the same application services and renders their results in terminal/JSON form.

---

## 9. Session and artifact management

Each opened source file should create an investigation session. A session should have a unique ID and preserve the source path and source SHA-256 at the time of analysis.

Suggested session directory:

```text
<chosen-output-directory>/
└── <session-id>_<source-basename>/
    ├── session.json
    ├── analysis.json
    ├── report.md
    ├── artifacts/
    │   ├── visual/
    │   ├── extracted/
    │   ├── strings/
    │   └── tool-output/
    └── logs/
```

Rules:
- Default to a user-writable application workspace, with a setting to choose another output directory.
- Do not silently copy over, rename, or edit the source file.
- Do not assume the source remains at the same path forever; record its original path, size, modified timestamp, and hash.
- Save derived images and extracted content only under the session artifact directory unless the user explicitly exports elsewhere.
- Use safe, collision-resistant artifact filenames.
- Store relative artifact paths in the session manifest and report.
- Save structured data as JSON so a later CLI or another frontend can reuse it.
- Make it possible to reopen a saved session in a later release, but full session reopening is not a blocker for the first prototype if the schema is versioned from the beginning.

---

## 10. Security, reliability, and evidence-handling requirements

The tool will process untrusted challenge files. Treat all inputs and extracted data as untrusted.

### 10.1 Source preservation

- Open source files read-only.
- Never write transformed data back to the source path.
- Never automatically overwrite a user-selected output file.
- Calculate and retain SHA-256 before analysis; optionally re-check it at the end to detect unexpected source changes.

### 10.2 Parser and resource limits

- Handle malformed files without crashing the GUI.
- Set configurable limits for maximum input size, decoded pixel count, and generated artifact size.
- Handle Pillow decompression-bomb warnings/errors explicitly.
- Avoid loading unnecessarily large files entirely into memory when streaming is practical (hashing and byte scans should support chunked reads).
- Put timeouts on external-tool calls.
- Allow the user to cancel long-running tasks.
- Limit recursive or nested extraction; recursive archive analysis is out of MVP scope.

### 10.3 External process safety

- Invoke external tools with argument arrays, not `shell=True` or concatenated shell commands.
- Validate executable availability and supported arguments.
- Capture standard output, standard error, exit code, and timeout state.
- Sanitize display of tool output; treat it as untrusted text.
- Never execute extracted binaries, scripts, documents, or macros.
- Never automatically open a URL discovered in an image.
- Do not log passwords or passphrases.

### 10.4 Error handling

Errors should be local to the affected operation. A failed ExifTool call should not prevent the Structure page from working. Present errors in plain language, preserve technical details in an expandable diagnostic view, and record a structured error state in the session.

---

## 11. Configuration and usability

Provide a Settings dialog or page with at least:
- Default output/workspace directory.
- Maximum file size and pixel-count safeguards.
- Default minimum string length.
- Custom flag-pattern list.
- External tool paths/overrides where auto-detection fails.
- Theme selection if both dark and light themes are implemented.
- Whether Deep Scan should generate visual previews automatically (default off).

Keyboard shortcuts to support:
- `Ctrl+O`: Open image.
- `Ctrl+R`: Run Quick Scan.
- `Ctrl+Shift+R`: Run Deep Scan.
- `Ctrl+S`: Export/save current report or session, with a clear dialog if destination is needed.
- `Esc`: Close a dialog or cancel a cancellable task where appropriate.

Use clear empty states. Every disabled feature should explain why it is unavailable (for example, unsupported format or missing optional tool), rather than appearing broken.

---

## 12. Implementation roadmap

Implement in small, testable milestones. Do not attempt to build every module and the complete GUI in one pass.

### Phase 0 — Repository and application skeleton

Deliver:
- Python project structure and `pyproject.toml`.
- PySide6 main window.
- Welcome/empty state and file picker.
- Drag-and-drop file loading.
- Basic theme and navigation shell.
- Runtime tool discovery/status display.

Exit criteria:
- Application launches from a documented command.
- User can open a supported image and see its filename.
- GUI remains responsive while loading a reasonably large image.
- Missing optional tools do not prevent launch.

### Phase 1 — Core identification, hashes, and Overview

Deliver:
- Actual format identification.
- Basic image properties and preview.
- SHA-256, MD5, and SHA-1 calculation.
- Quick Scan orchestration and progress display.
- Overview findings/observations panel.
- Session model and basic JSON persistence.

Exit criteria:
- Correctly identifies PNG, JPEG, BMP, and GIF fixtures by content.
- Detects an extension mismatch.
- Hashes match known test vectors or independently verified results.
- Handles an unreadable file without crashing.

### Phase 2 — Metadata Inspector

Deliver:
- Pillow metadata fallback.
- Optional ExifTool adapter.
- Normalized metadata table and raw values.
- Tool status and error states.

Exit criteria:
- Works with and without ExifTool.
- Missing metadata is clearly distinguished from extraction failure.
- Raw values are retained and searchable.

### Phase 3 — File Structure Analyzer

Deliver:
- Generic signature and boundary checks.
- PNG chunk parser.
- JPEG marker parser.
- Basic BMP/GIF structural information.
- Trailing-data detection.
- Hex viewer linked to selected offsets.
- Optional Binwalk integration.

Exit criteria:
- Parser offsets and lengths are validated against known fixtures.
- PNG trailing data after `IEND` is found and reported accurately.
- JPEG trailing data after the EOI marker is found and reported accurately.
- Malformed files return warnings/errors rather than crashing the application.

### Phase 4 — Visual Lab

Deliver:
- RGB and alpha channel views.
- Grayscale and inversion.
- All 24 RGB bit-plane views.
- Histograms.
- Zoom/pan and derived-image export.

Exit criteria:
- Channel and bit-plane outputs match independently computed expected arrays for test images.
- Derived views never alter the source.
- Generation happens in a worker and does not freeze the GUI.

### Phase 5 — Strings & Payloads

Deliver:
- ASCII/UTF-8/UTF-16 extraction.
- Offset-aware results.
- URL/IP/email candidates.
- Base64-like candidate detection and optional decode preview.
- Configurable CTF flag patterns.

Exit criteria:
- Test strings are found in all supported encodings.
- Offsets point to the correct source bytes.
- Decoding is preview-only and never executes content.

### Phase 6 — Steganography Scanner

Deliver:
- Basic configurable LSB extraction.
- zsteg adapter.
- Steghide adapter for applicable formats.
- Binwalk/signature-scan integration.
- Results table, method applicability, and artifact storage.

Exit criteria:
- Each integration reports unavailable, unsupported, failed, or completed accurately.
- Known test fixtures verify extraction paths and parameters.
- Passphrases never appear in logs or reports.
- Extracted content is never executed automatically.

### Phase 7 — Reporting and polish

Deliver:
- Markdown report generator.
- JSON export.
- User notes and finding review states.
- Session artifact organisation.
- UI refinements and regression tests.

Exit criteria:
- Exported report accurately reflects which checks ran and which did not.
- Artifact links resolve inside the exported investigation folder.
- Report does not contain secret inputs.
- A complete investigation can be reviewed without relying on the live GUI state.

### Phase 8 — Packaging and future CLI preparation

Deliver:
- Packaging experiment for at least one target OS.
- Installation and troubleshooting documentation.
- Confirmed separation between UI and analysis engine.
- Architecture notes for adding a future CLI.

The CLI itself is explicitly outside this initial GUI build.

---

## 13. Testing strategy

Create a small, curated fixture corpus. Include both normal images and deliberately constructed forensic test cases.

### 13.1 Fixture categories

- Normal PNG, JPEG, BMP, and GIF files.
- Files with misleading extensions.
- Images with EXIF metadata and images with no metadata.
- PNG files with text chunks.
- PNG files with appended bytes after `IEND`.
- JPEG files with common metadata segments and appended bytes after EOI.
- Truncated and malformed PNG/JPEG files.
- Images with alpha channels.
- Images with controlled pixel patterns for channel/bit-plane tests.
- Images containing known printable strings or encoded test strings in their byte streams.
- Small, safe test files with known embedded signatures.
- Test images containing known LSB payloads generated specifically for unit testing.

Do not use private or sensitive user images as committed fixtures. Generate synthetic test files or use appropriately licensed samples.

### 13.2 Test levels

**Unit tests**
- Hashing.
- Format identification.
- PNG/JPEG parser offsets and boundaries.
- Entropy calculations.
- Channel and bit-plane extraction.
- String extraction and offset calculation.
- Finding serialization.

**Integration tests**
- External-tool adapter behaviour with tools installed and absent.
- Timeouts, non-zero exit codes, and malformed tool output.
- Session artifact creation.
- Markdown and JSON report generation.

**GUI tests**
- Launch and initial state.
- Open file and navigate pages.
- Start/cancel a scan.
- Display a failed/missing optional tool state.
- Save a derived image and export a report.

**Manual checks**
- Test on Windows and Linux.
- Test dark theme readability at common screen sizes and display scaling.
- Test paths with spaces and non-ASCII characters.
- Test large images and malformed inputs.

---

## 14. MVP scope and explicit non-goals

### MVP must include

- Desktop GUI built with PySide6.
- File picker and drag-and-drop.
- PNG, JPEG, BMP, and GIF identification and basic support.
- Overview with hashes and image properties.
- Metadata Inspector with fallback behaviour.
- PNG/JPEG structure parsing, basic BMP/GIF properties, and trailing-data checks where applicable.
- Hex view linked to structure offsets.
- RGB/alpha channel views and 24 RGB bit planes.
- Histograms.
- Strings extraction and basic candidate detection.
- Basic LSB extraction.
- Optional integrations for ExifTool, Binwalk, zsteg, and Steghide.
- Findings model, session storage, Markdown report, JSON export.
- Safe handling of untrusted files and responsive background tasks.

### Explicitly out of scope for the first GUI release

- Full disk or filesystem forensics.
- Network/PCAP forensics.
- Audio steganography or SSTV analysis.
- Video analysis.
- APK/mobile application analysis.
- Automated OSINT or internet lookups.
- Automatic flag solving or claims that a flag has been found.
- Password brute forcing.
- Recursive archive extraction and recursive payload analysis.
- Automatic execution of extracted content.
- Cloud accounts, collaboration, or multi-user case management.
- A separate CLI implementation.

These may be considered as future modules, but they must not delay the initial image-analysis workbench.

---

## 15. Definition of done for the first usable release

The first usable release is complete when a user can:

1. Launch the desktop application on Linux and Windows from documented instructions.
2. Open or drag in a PNG/JPEG/BMP/GIF and see its actual format, preview, dimensions, file size, and hashes.
3. Review available metadata and understand whether a field is absent, unsupported, or failed to extract.
4. Inspect PNG chunks or JPEG markers and jump from a suspicious structure row to its byte offset in the hex viewer.
5. Identify appended data after the relevant PNG/JPEG end marker.
6. View RGB channels, alpha where present, all 24 RGB bit planes, and histograms.
7. Extract and search printable strings, with offsets and basic candidate classification.
8. Run applicable basic/optional steganography checks and see exactly which methods ran.
9. Save derived images and extracted files without modifying the original.
10. Export a Markdown report and JSON session data containing the checks, findings, parameters, and artifact references.
11. Continue using core features when optional external tools are not installed.
12. Use the application without the GUI freezing during analysis.

---

## 16. Instructions for the AI coding agent

Use this plan as the implementation specification. Follow these instructions throughout development:

1. **Inspect before changing:** inspect the repository, Python version, operating system, and existing files before creating or replacing project files. Do not assume the repository is empty.
2. **Build incrementally:** implement one roadmap phase at a time. Keep the application runnable at the end of each phase.
3. **Do not create a monolithic file:** preserve the proposed layer boundaries and keep modules small and cohesive.
4. **Keep the GUI thin:** widgets must call application services; they must not contain parser logic, hashing logic, or direct subprocess calls.
5. **Use typed, shared result models:** modules must return structured results and findings, not UI-specific strings alone.
6. **Test forensic correctness:** do not rely on screenshots or visual plausibility. Test offsets, lengths, hashes, and pixel arrays against known fixtures.
7. **Verify third-party tool behaviour:** check the installed tool's actual command syntax and version. Do not invent flags or assume output formats. Make adapters tolerant of version differences where reasonable.
8. **Handle absence gracefully:** optional tools are optional in code, documentation, and UI. The application must still launch without them.
9. **Preserve evidence:** never modify the source image, never execute extracted content, and never store passphrases.
10. **Avoid unsupported claims:** findings must state what the tool observed and how it observed it. A heuristic match is a lead, not a verdict.
11. **Document setup:** maintain a README with supported platforms, prerequisites, installation, launch, optional-tool setup, tests, and known limitations.
12. **Report progress with concrete outputs:** after each phase, summarize files created/changed, tests run, known limitations, and the next phase. Do not claim a feature is complete until it has been exercised by tests or a documented manual check.

### Recommended first coding task

Start with **Phase 0 only**. Build the project skeleton, PySide6 main window, navigation shell, welcome page, file picker, drag-and-drop handling, and optional-tool status display. Do not begin implementing every forensic module at once. Once Phase 0 is runnable and tested, proceed to Phase 1.

---

## 17. Important product decision summary

- The initial product is a **GUI-first desktop application**.
- PySide6 is the selected GUI framework.
- The interface is a modern forensic workstation with a sidebar, central analysis pages, and a collapsible evidence inspector.
- Python modules form a reusable analysis engine, independent of Qt.
- A CLI-only build is a later frontend, not a separate implementation.
- The initial focus is image triage and investigation for personal digital-forensics/CTF use.
- The priority modules are Metadata, File Structure, Visual Lab, Steganography, Strings & Payloads, and Reporting.
- Optional external tools improve coverage but must never be mandatory for launching or using the core application.
- The source image is always preserved; all derived data belongs in the investigation session workspace.
