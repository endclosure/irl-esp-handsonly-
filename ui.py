## THIS IS MADE BY TERRIFIED discord.gg/nixstudios - https://github.com/endclosure


import time
import threading
import cv2

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QGroupBox,
)

from camera import Camera, list_cameras
from detector import PoseDetector
from esp import draw_esp


class CaptureWorker:
    def __init__(self, camera: Camera, detector: PoseDetector):
        self.camera   = camera
        self.detector = detector
        self.running  = False

        self._opt_lock     = threading.Lock()
        self.show_box      = True
        self.show_skeleton = True

        self._raw_lock  = threading.Lock()
        self._raw_frame = None

        self._out_lock    = threading.Lock()
        self._out_frame   = None
        self._out_count   = 0

        self._fps       = 0.0
        self._last_time = time.perf_counter()

        self._capture_thread  = None
        self._detect_thread   = None
        self._detect_event    = threading.Event()

    def start(self):
        self.running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._detect_thread  = threading.Thread(target=self._detect_loop,  daemon=True)
        self._capture_thread.start()
        self._detect_thread.start()

    def stop(self):
        self.running = False
        self._detect_event.set()
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
        if self._detect_thread:
            self._detect_thread.join(timeout=2.0)
        self._capture_thread = None
        self._detect_thread  = None

    def _capture_loop(self):
        while self.running:
            ok, frame = self.camera.read()
            if not ok:
                self.running = False
                break
            with self._raw_lock:
                self._raw_frame = frame
            self._detect_event.set()

    def _detect_loop(self):
        while self.running:
            self._detect_event.wait()
            self._detect_event.clear()

            if not self.running:
                break

            with self._raw_lock:
                frame = self._raw_frame

            if frame is None:
                continue

            detections = self.detector.detect(frame)

            with self._opt_lock:
                show_box      = self.show_box
                show_skeleton = self.show_skeleton

            rendered = draw_esp(frame.copy(), detections,
                                show_box=show_box,
                                show_skeleton=show_skeleton)

            now   = time.perf_counter()
            delta = now - self._last_time
            if delta > 0:
                self._fps = self._fps * 0.85 + (1.0 / delta) * 0.15
            self._last_time = now

            with self._out_lock:
                self._out_frame = rendered
                self._out_count = len(detections)

    def pop_frame(self):
        with self._out_lock:
            frame = self._out_frame
            count = self._out_count
            self._out_frame = None
            return frame, count

    @property
    def fps(self):
        return self._fps

    def set_options(self, show_box: bool, show_skeleton: bool):
        with self._opt_lock:
            self.show_box      = show_box
            self.show_skeleton = show_skeleton


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ESP PREVIEW")
        self.resize(1100, 760)

        self.camera   = None
        self.detector = None
        self.worker   = None

        root   = QWidget()
        layout = QVBoxLayout(root)

        header = QHBoxLayout()
        title  = QLabel("ESP PREVIEW")
        title.setStyleSheet("color: #f5bbfd; font-size: 25px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        self.status = QLabel("STOPPED")
        self.status.setStyleSheet("color: #ff8b9b;")
        header.addWidget(self.status)
        layout.addLayout(header)

        controls = QHBoxLayout()
        self.camera_select = QComboBox()
        self.refresh_cameras()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_cameras)
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_camera)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_camera)
        self.stop_button.setEnabled(False)
        controls.addWidget(QLabel("Camera:"))
        controls.addWidget(self.camera_select, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.preview = QLabel("Select a camera and press Start")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(640, 420)
        self.preview.setStyleSheet("""
            background: #08080b;
            border: 1px solid #403044;
            border-radius: 8px;
            color: #aaaaaa;
        """)
        layout.addWidget(self.preview, 1)

        options       = QGroupBox("ESP Settings")
        option_layout = QHBoxLayout(options)
        self.box_check = QCheckBox("2D Bounding Box")
        self.box_check.setChecked(True)
        self.box_check.toggled.connect(self._sync_options)
        self.skeleton_check = QCheckBox("Skeleton")
        self.skeleton_check.setChecked(True)
        self.skeleton_check.toggled.connect(self._sync_options)
        self.fps_label = QLabel("FPS: --")
        option_layout.addWidget(self.box_check)
        option_layout.addWidget(self.skeleton_check)
        option_layout.addStretch()
        option_layout.addWidget(self.fps_label)
        layout.addWidget(options)

        self.setCentralWidget(root)

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111116; color: #eeeeF5; }
            QPushButton {
                background: #29212d;
                border: 1px solid #604665;
                padding: 9px 16px;
                border-radius: 6px;
            }
            QPushButton:hover    { background: #49334d; }
            QPushButton:disabled { color: #666666; }
            QComboBox {
                background: #211d25;
                padding: 8px;
                border: 1px solid #604665;
            }
            QGroupBox {
                border: 1px solid #604665;
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title { color: #f5bbfd; }
        """)

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._refresh_ui)
        self._ui_timer.setInterval(8)

    def refresh_cameras(self):
        current = self.camera_select.currentData()
        self.camera_select.clear()
        cameras = list_cameras()
        for index, name in cameras:
            self.camera_select.addItem(name, index)
        if current is not None:
            pos = self.camera_select.findData(current)
            if pos >= 0:
                self.camera_select.setCurrentIndex(pos)
        if not cameras:
            self.camera_select.addItem("No cameras found", -1)

    def start_camera(self):
        index = self.camera_select.currentData()
        if index is None or index < 0:
            QMessageBox.warning(self, "Camera", "No working camera was found.")
            return

        try:
            self.camera   = Camera(index)
            self.detector = PoseDetector()
        except Exception as err:
            self.stop_camera()
            QMessageBox.critical(self, "Error", str(err))
            return

        self.worker = CaptureWorker(self.camera, self.detector)
        self.worker.set_options(self.box_check.isChecked(),
                                self.skeleton_check.isChecked())
        self.worker.start()
        self._ui_timer.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.camera_select.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.status.setText("RUNNING")
        self.status.setStyleSheet("color: #8df0ae;")

    def stop_camera(self):
        self._ui_timer.stop()

        if self.worker:
            self.worker.stop()
            self.worker = None
        if self.camera:
            self.camera.release()
            self.camera = None
        if self.detector:
            self.detector.close()
            self.detector = None

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.camera_select.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.status.setText("STOPPED")
        self.status.setStyleSheet("color: #ff8b9b;")
        self.fps_label.setText("FPS: --")
        self.preview.setPixmap(QPixmap())
        self.preview.setText("Select a camera and press Start")

    def _refresh_ui(self):
        if not self.worker:
            return

        frame, count = self.worker.pop_frame()
        if frame is None:
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image  = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)

        self.preview.setPixmap(
            pixmap.scaled(self.preview.size(),
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.FastTransformation)
        )

        self.fps_label.setText(f"FPS: {self.worker.fps:.0f} | Hands: {count}")

    def _sync_options(self):
        if self.worker:
            self.worker.set_options(self.box_check.isChecked(),
                                    self.skeleton_check.isChecked())

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
