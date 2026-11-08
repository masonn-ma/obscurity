from __future__ import annotations

import io
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox, QProgressBar, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget

from obscurity.analysis.visual import derived_views
from obscurity.application.service import InvestigationService
from obscurity.domain.models import AnalysisSession
from obscurity.reporting.reports import export_session, export_session_to_path, render_markdown


class WorkSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class Work(QRunnable):
    def __init__(self, callback) -> None:
        super().__init__()
        self.callback = callback
        self.signals = WorkSignals()

    def run(self) -> None:
        try:
            self.signals.completed.emit(self.callback())
        except Exception as error:
            self.signals.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.service = InvestigationService()
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("Obscurity - Image Forensics")
        self.setMinimumSize(1100, 700)
        self.setAcceptDrops(True)
        self._build_ui()
        self._show_welcome()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>OBSCURITY</b>  /  image investigation"))
        self.open_button, self.quick_button, self.deep_button, self.export_button = (QPushButton(text) for text in ("Open Image", "Run Quick Scan", "Run Deep Scan", "Export Report"))
        for button in (self.open_button, self.quick_button, self.deep_button, self.export_button):
            top.addWidget(button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        top.addWidget(self.progress)
        root.addLayout(top)
        body = QHBoxLayout()
        self.navigation = QListWidget()
        self.navigation.addItems(["Overview", "Metadata", "File Structure", "Visual Lab", "Steganography", "Strings & Payloads", "Report"])
        self.navigation.setMaximumWidth(190)
        body.addWidget(self.navigation)
        self.pages = QStackedWidget()
        self.welcome = self._label_page("Drop an image here or choose Open Image.")
        self.overview = self._label_page("")
        self.metadata = self._table_page(["Group", "Key", "Value", "Status"])
        self.structure = self._table_page(["Offset", "Length", "Component", "Description", "Status"])
        self.visual, self.visual_list, self.visual_viewer, self.visual_status, self.save_visual_button = self._visual_page()
        self.stego = self._label_page("Basic LSB extraction and optional tools are available from the analysis engine.")
        self.strings = self._table_page(["Offset", "Encoding", "Kind", "Value"])
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        for page in (self.welcome, self.overview, self.metadata, self.structure, self.visual, self.stego, self.strings, self.report):
            self.pages.addWidget(page)
        body.addWidget(self.pages, 1)
        root.addLayout(body, 1)
        self.status = QLabel("No source loaded")
        root.addWidget(self.status)
        self.setCentralWidget(central)
        self.open_button.clicked.connect(lambda: self.open_image())
        self.quick_button.clicked.connect(lambda: self._run_scan(False))
        self.deep_button.clicked.connect(lambda: self._run_scan(True))
        self.export_button.clicked.connect(self.export_report)
        self.visual_list.currentTextChanged.connect(self._show_visual)
        self.save_visual_button.clicked.connect(self._save_visual)
        self.navigation.currentRowChanged.connect(lambda row: self.pages.setCurrentIndex(row + 1 if self.service.session else 0))
        self.setStyleSheet("QWidget { background: #20252b; color: #e7ebef; } QPushButton { background: #33404d; border: 1px solid #536474; padding: 7px 12px; border-radius: 3px; } QListWidget, QTableWidget, QTextEdit { background: #171b20; border: 1px solid #3c4650; } QHeaderView::section { background: #303943; padding: 5px; }")

    def _label_page(self, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)
        page.label = label  # type: ignore[attr-defined]
        return page

    def _table_page(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSortingEnabled(True)
        return table

    def _visual_page(self) -> tuple[QWidget, QListWidget, QLabel, QLabel, QPushButton]:
        page = QWidget()
        layout = QVBoxLayout(page)
        heading = QLabel("<h2>Visual Lab</h2><p>Select a derived view to inspect channels and bit planes.</p>")
        layout.addWidget(heading)
        content = QHBoxLayout()
        view_list = QListWidget()
        view_list.setMinimumWidth(180)
        content.addWidget(view_list)
        viewer = QLabel("Open an image to generate visual views.")
        viewer.setAlignment(Qt.AlignCenter)
        viewer.setMinimumSize(500, 400)
        viewer.setStyleSheet("background: #11151a; border: 1px solid #3c4650;")
        content.addWidget(viewer, 1)
        layout.addLayout(content, 1)
        footer = QHBoxLayout()
        status = QLabel("No derived view selected")
        save_button = QPushButton("Save Derived Image")
        save_button.setEnabled(False)
        footer.addWidget(status)
        footer.addStretch()
        footer.addWidget(save_button)
        layout.addLayout(footer)
        page.view_list = view_list  # type: ignore[attr-defined]
        return page, view_list, viewer, status, save_button

    def _show_welcome(self) -> None:
        self.pages.setCurrentWidget(self.welcome)
        for button in (self.quick_button, self.deep_button, self.export_button):
            button.setEnabled(False)

    def open_image(self, path: Path | None = None) -> None:
        if path is None:
            selected, _ = QFileDialog.getOpenFileName(self, "Open image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All files (*)")
            if not selected:
                return
            path = Path(selected)
        try:
            session = self.service.open(path)
        except Exception as error:
            QMessageBox.critical(self, "Unable to open image", str(error))
            return
        self._render_session(session)
        self._run_scan(False)

    def _run_scan(self, deep: bool) -> None:
        if not self.service.session:
            return
        self.progress.show()
        self.quick_button.setEnabled(False)
        self.deep_button.setEnabled(False)
        work = Work(self.service.deep_scan if deep else self.service.quick_scan)
        work.signals.completed.connect(self._scan_complete)
        work.signals.failed.connect(self._scan_failed)
        self.thread_pool.start(work)

    def _scan_complete(self, session: AnalysisSession) -> None:
        self.progress.hide()
        self.quick_button.setEnabled(True)
        self.deep_button.setEnabled(True)
        self._render_session(session)

    def _scan_failed(self, message: str) -> None:
        self.progress.hide()
        self.quick_button.setEnabled(True)
        self.deep_button.setEnabled(True)
        QMessageBox.critical(self, "Analysis failed", message)

    def _render_session(self, session: AnalysisSession) -> None:
        self.export_button.setEnabled(True)
        props = session.source.properties
        self.status.setText(f"{session.source.name} | {props.format} | SHA-256 {session.source.sha256[:16]}... | {session.scan_status}")
        preview = QPixmap(session.source.path)
        preview = preview.scaled(360, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.overview.label.setPixmap(preview)
        self.overview.label.setToolTip(f"{session.source.name}\n{props.format} {props.width} x {props.height}")  # type: ignore[attr-defined]
        self.overview.label.setText(f"<h2>{session.source.name}</h2><p>{props.format} {props.width} x {props.height} | {props.mode} | {session.source.size:,} bytes</p><p>SHA-256: {session.source.sha256}</p><p>{len(session.findings)} observations recorded.</p>")  # type: ignore[attr-defined]
        self._fill_table(self.metadata, [[i.group, i.key, i.value, i.status] for i in session.metadata])
        self._fill_table(self.structure, [[str(s.offset), str(s.length), s.component, s.description, s.status] for s in session.structure])
        self._fill_table(self.strings, [[str(i["offset"]), str(i["encoding"]), str(i["kind"]), str(i["value"])] for i in session.strings])
        self.report.setPlainText(render_markdown(session))
        self._load_visual_views()
        self.pages.setCurrentWidget(self.overview)

    def _load_visual_views(self) -> None:
        if self.service.session is None:
            return
        self.visual_list.clear()
        self.visual_list.addItem("Generating visual views...")
        self.visual_list.setEnabled(False)
        self.save_visual_button.setEnabled(False)
        work = Work(lambda: {
            name: self._image_bytes(image)
            for name, image in derived_views(Path(self.service.session.source.path)).items()
        })
        work.signals.completed.connect(self._visual_views_ready)
        work.signals.failed.connect(lambda message: self._visual_views_failed(message))
        self.thread_pool.start(work)

    @staticmethod
    def _image_bytes(image) -> bytes:
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()

    def _visual_views_ready(self, views: dict[str, bytes]) -> None:
        self.visual_views = views
        self.visual_list.clear()
        self.visual_list.addItems(views.keys())
        self.visual_list.setEnabled(True)
        self.visual_list.setCurrentRow(0)
        self.visual_status.setText(f"{len(views)} derived views ready")

    def _visual_views_failed(self, message: str) -> None:
        self.visual_list.clear()
        self.visual_list.addItem("Unable to generate views")
        self.visual_status.setText(message)

    def _show_visual(self, name: str) -> None:
        data = getattr(self, "visual_views", {}).get(name)
        if not data:
            self.save_visual_button.setEnabled(False)
            return
        pixmap = QPixmap()
        pixmap.loadFromData(data, "PNG")
        self.visual_viewer.setPixmap(pixmap.scaled(self.visual_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.visual_status.setText(f"{name} | {pixmap.width()} x {pixmap.height()}")
        self.save_visual_button.setEnabled(True)

    def _save_visual(self) -> None:
        name = self.visual_list.currentItem().text() if self.visual_list.currentItem() else ""
        data = getattr(self, "visual_views", {}).get(name)
        if not data:
            return
        target, _ = QFileDialog.getSaveFileName(self, "Save derived image", f"{name}.png", "PNG image (*.png)")
        if target:
            Path(target).write_bytes(data)

    def _fill_table(self, table: QTableWidget, rows: list[list[str]]) -> None:
        sorting = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for row in rows:
            index = table.rowCount()
            table.insertRow(index)
            for column, value in enumerate(row):
                table.setItem(index, column, QTableWidgetItem(value))
        table.setSortingEnabled(sorting)

    def export_report(self) -> None:
        if self.service.session is None or self.service.directory is None:
            return
        default_report = self.service.directory / "report.md"
        choice = QMessageBox(self)
        choice.setWindowTitle("Export report")
        choice.setText("Choose where to save the investigation report.")
        choice.setInformativeText(f"Default location:\n{default_report}")
        default_button = choice.addButton("Use Default Path", QMessageBox.AcceptRole)
        custom_button = choice.addButton("Choose Custom Path", QMessageBox.ActionRole)
        choice.addButton(QMessageBox.Cancel)
        choice.exec()
        try:
            if choice.clickedButton() is default_button:
                markdown, session_json = export_session(self.service.session, self.service.directory)
            elif choice.clickedButton() is custom_button:
                selected, _ = QFileDialog.getSaveFileName(self, "Save investigation report", "report.md", "Markdown report (*.md)")
                if not selected:
                    return
                markdown, session_json = export_session_to_path(self.service.session, Path(selected))
            else:
                return
        except OSError as error:
            QMessageBox.critical(self, "Report export failed", str(error))
            return
        QMessageBox.information(self, "Report exported", f"Markdown report:\n{markdown}\n\nJSON session data:\n{session_json}")

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.open_image(Path(urls[0].toLocalFile()))
