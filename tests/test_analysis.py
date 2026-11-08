from pathlib import Path

from PIL import Image

from obscurity.analysis.core import calculate_hashes, identify_image
from obscurity.analysis.metadata import read_metadata
from obscurity.analysis.stego import extract_lsb
from obscurity.analysis.strings import extract_strings
from obscurity.analysis.structure import parse_png
from obscurity.analysis.visual import derived_views
from obscurity.application.service import InvestigationService
from obscurity.reporting.reports import export_session_to_path


def make_png(tmp_path: Path) -> Path:
    path = tmp_path / "sample.png"
    Image.new("RGBA", (2, 2), (255, 0, 128, 255)).save(path)
    return path


def test_identification_and_hashes(tmp_path: Path) -> None:
    path = make_png(tmp_path)
    props = identify_image(path)
    assert props.format == "PNG"
    assert (props.width, props.height) == (2, 2)
    assert len(calculate_hashes(path)["sha256"]) == 64


def test_pillow_metadata_has_keys_and_values(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("obscurity.analysis.metadata.shutil.which", lambda _: None)
    items = read_metadata(make_png(tmp_path))
    values = {item.key: item.value for item in items}
    assert values["Format"] == "PNG"
    assert values["Width"] == "2"
    assert values["Height"] == "2"


def test_png_trailing_bytes_are_reported(tmp_path: Path) -> None:
    path = make_png(tmp_path)
    segments, findings = parse_png(path.read_bytes() + b"PAYLOAD")
    assert segments[-1].component == "IEND"
    finding = next(item for item in findings if "after PNG" in item.title)
    assert finding.evidence["bytes"] == 7


def test_string_offsets_and_candidates() -> None:
    results = extract_strings(b"\x00http://example.test\x00")
    assert results[0]["offset"] == 1
    assert results[0]["kind"] == "URL candidate"


def test_lsb_extraction_is_deterministic(tmp_path: Path) -> None:
    result = extract_lsb(make_png(tmp_path), "RGB", 0)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_visual_views_include_all_rgb_bit_planes(tmp_path: Path) -> None:
    views = derived_views(make_png(tmp_path))
    assert len(views) == 30
    assert "red" in views
    assert "r-bit-0" in views
    assert "b-bit-7" in views
    assert "alpha" in views


def test_open_button_does_not_pass_clicked_boolean_to_pillow() -> None:
    from PySide6.QtWidgets import QApplication
    from obscurity.ui.main_window import MainWindow

    QApplication.instance() or QApplication([])
    window = MainWindow()
    received = []
    window.open_image = lambda path=None: received.append(path)
    window.open_button.clicked.emit()
    assert received == [None]


def test_custom_report_path_writes_markdown_and_json(tmp_path: Path) -> None:
    source = make_png(tmp_path)
    service = InvestigationService()
    session = service.open(source)
    markdown, session_json = export_session_to_path(session, tmp_path / "exports" / "investigation.txt")
    assert markdown == tmp_path / "exports" / "investigation.md"
    assert session_json == tmp_path / "exports" / "investigation.json"
    assert markdown.exists()
    assert session_json.exists()
