import sys
import os
import subprocess
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFileDialog, QSlider, QLabel,
                             QMessageBox, QStyle, QLineEdit)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor, QIntValidator
import mpv


# --- Helper Function to format time ---
def format_time(seconds):
    """Converts seconds to HH:MM:SS.mmm format"""
    if seconds is None:
        return "00:00:00.000"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

class VideoCropper(QWidget):
    def __init__(self):
        super().__init__()
        self.input_file = None
        self.duration_sec = 0
        self.start_time_sec = 0.0
        self.end_time_sec = 0.0
        self.player = None

        if not os.path.exists('mpv-2.dll'):
            self.show_error_message(
                "错误",
                "未在程序同级目录找到 mpv-2.dll。\n请从 libmpv 开发包中获取并放置在正确位置。"
            )
            QTimer.singleShot(100, self.close)
            return

        self.init_ui()
        self.init_mpv()

    def init_ui(self):
        self.setWindowTitle('视频裁剪与音频提取工具')
        self.setGeometry(100, 100, 800, 650)
        
        main_layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        time_button_layout = QHBoxLayout()
        seek_layout = QHBoxLayout()
        # --- NEW: Layout for the time jump input boxes ---
        jump_input_layout = QHBoxLayout()

        self.video_widget = QWidget()
        self.video_widget.setMinimumSize(640, 360)
        palette = self.video_widget.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.video_widget.setPalette(palette)
        self.video_widget.setAutoFillBackground(True)

        self.start_time_label = QLabel("开始: 00:00:00.000")
        self.end_time_label = QLabel("结束: 00:00:00.000")
        self.current_time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self.current_time_label.setAlignment(Qt.AlignCenter)

        self.seek_bwd_btn = QPushButton("快退 0.5s")
        self.seek_bwd_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekBackward))
        self.seek_bwd_btn.clicked.connect(self.seek_backward)
        
        self.seek_fwd_btn = QPushButton("快进 0.5s")
        self.seek_fwd_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward))
        self.seek_fwd_btn.clicked.connect(self.seek_forward)
        
        seek_layout.addStretch(1)
        seek_layout.addWidget(self.seek_bwd_btn)
        seek_layout.addWidget(self.current_time_label)
        seek_layout.addWidget(self.seek_fwd_btn)
        seek_layout.addStretch(1)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.seek_video)
        
        self.import_btn = QPushButton("导入视频")
        self.import_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.import_btn.clicked.connect(self.import_video)
        
        self.set_start_btn = QPushButton("设为开始点")
        self.set_end_btn = QPushButton("设为结束点")
        self.set_start_btn.clicked.connect(self.set_start_time)
        self.set_end_btn.clicked.connect(self.set_end_time)
        
        # --- NEW: Audio Extraction Button ---
        self.extract_audio_btn = QPushButton("提取音频")
        self.extract_audio_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.extract_audio_btn.clicked.connect(self.extract_audio)
        
        self.crop_btn = QPushButton("裁剪视频")
        self.crop_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.crop_btn.clicked.connect(self.crop_video)

        # --- NEW: Separated Time Jump Inputs ---
        self.jump_h_input = QLineEdit()
        self.jump_m_input = QLineEdit()
        self.jump_s_input = QLineEdit()
        for inp, placeholder in [(self.jump_h_input, "时"), (self.jump_m_input, "分"), (self.jump_s_input, "秒")]:
            inp.setPlaceholderText(placeholder)
            inp.setValidator(QIntValidator(0, 999)) # Allow only numbers
            inp.setFixedWidth(40)
        
        self.jump_btn = QPushButton("跳转")
        self.jump_btn.clicked.connect(self.jump_to_time)

        # Disable all controls initially
        self.set_controls_enabled(False)

        time_button_layout.addWidget(self.start_time_label)
        time_button_layout.addStretch(1)
        time_button_layout.addWidget(self.set_start_btn)
        time_button_layout.addWidget(self.set_end_btn)
        time_button_layout.addStretch(1)
        time_button_layout.addWidget(self.end_time_label)
        
        # --- MODIFIED: control_layout with all new controls ---
        jump_input_layout.setSpacing(2)
        jump_input_layout.addWidget(QLabel("跳转到:"))
        jump_input_layout.addWidget(self.jump_h_input)
        jump_input_layout.addWidget(self.jump_m_input)
        jump_input_layout.addWidget(self.jump_s_input)
        jump_input_layout.addWidget(self.jump_btn)
        
        control_layout.addWidget(self.import_btn)
        control_layout.addStretch(1)
        control_layout.addLayout(jump_input_layout)
        control_layout.addStretch(1)
        control_layout.addWidget(self.extract_audio_btn)
        control_layout.addWidget(self.crop_btn)
        
        main_layout.addWidget(self.video_widget)
        main_layout.addLayout(seek_layout)
        main_layout.addWidget(self.slider)
        main_layout.addLayout(time_button_layout)
        main_layout.addLayout(control_layout)
        self.setLayout(main_layout)

    def set_controls_enabled(self, enabled):
        """Helper function to enable/disable all relevant controls."""
        self.slider.setEnabled(enabled)
        self.set_start_btn.setEnabled(enabled)
        self.set_end_btn.setEnabled(enabled)
        self.crop_btn.setEnabled(enabled)
        self.seek_bwd_btn.setEnabled(enabled)
        self.seek_fwd_btn.setEnabled(enabled)
        self.jump_h_input.setEnabled(enabled)
        self.jump_m_input.setEnabled(enabled)
        self.jump_s_input.setEnabled(enabled)
        self.jump_btn.setEnabled(enabled)
        self.extract_audio_btn.setEnabled(enabled)

    def init_mpv(self):
        try:
            self.player = mpv.MPV(
                wid=str(int(self.video_widget.winId())),
                vo='gpu', input_default_bindings=True, osd_level=3
            )
            self.player.observe_property('time-pos', self.on_time_update)
            self.player.observe_property('duration', self.on_duration_change)
        except Exception as e:
            self.show_error_message("MPV 初始化失败", f"错误: {e}")

    def import_video(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.mkv *.avi *.mov *.flv)")
        if filepath:
            self.input_file = filepath
            self.setWindowTitle(f'视频裁剪与音频提取 - {os.path.basename(self.input_file)}')
            self.player.play(self.input_file)
            self.player.pause = True
            self.start_time_sec = 0.0
            self.end_time_sec = 0.0
            self.start_time_label.setText("开始: 00:00:00.000")
            self.end_time_label.setText("结束: 00:00:00.000")
            self.set_controls_enabled(True)

    def seek_backward(self):
        if self.player:
            self.player.seek(-0.5, reference='relative', precision='exact')

    def seek_forward(self):
        if self.player:
            self.player.seek(0.5, reference='relative', precision='exact')

    def jump_to_time(self):
        if not self.player: return
        try:
            # Read from each box, defaulting to '0' if empty.
            h = int(self.jump_h_input.text() or '0')
            m = int(self.jump_m_input.text() or '0')
            s = float(self.jump_s_input.text() or '0')
            
            total_seconds = h * 3600 + m * 60 + s
            if total_seconds < 0: raise ValueError("Time cannot be negative.")

            seek_time = max(0, min(total_seconds, self.duration_sec))
            self.player.seek(seek_time, reference='absolute', precision='exact')
            
        except (ValueError, IndexError):
            self.show_error_message("时间格式错误", "请输入有效的数字。")

    def on_time_update(self, name, value):
        if value is not None and self.duration_sec > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(int(value * 1000))
            self.slider.blockSignals(False)
            self.current_time_label.setText(f"{format_time(value)} / {format_time(self.duration_sec)}")

    def on_duration_change(self, name, value):
        if value is not None and value > 0:
            self.duration_sec = value
            self.end_time_sec = value
            self.slider.setRange(0, int(value * 1000))
            self.end_time_label.setText(f"结束: {format_time(self.duration_sec)}")

    def seek_video(self, position):
        if self.player:
            seek_time = position / 1000.0
            self.player.seek(seek_time, reference='absolute', precision='exact')

    def set_start_time(self):
        if self.player and self.player.time_pos is not None:
            self.start_time_sec = self.player.time_pos
            self.start_time_label.setText(f"开始: {format_time(self.start_time_sec)}")

    def set_end_time(self):
        if self.player and self.player.time_pos is not None:
            self.end_time_sec = self.player.time_pos
            self.end_time_label.setText(f"结束: {format_time(self.end_time_sec)}")
            
    def _run_ffmpeg_command(self, command, output_file, process_name):
        """Helper function to run ffmpeg commands and handle errors."""
        try:
            msg_box = QMessageBox(QMessageBox.Information, f"正在{process_name}", f"正在处理，请稍候...\n输出文件: {output_file}", QMessageBox.NoButton, self)
            msg_box.show()
            QApplication.processEvents()
            
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            process = subprocess.run(
                command, check=True, capture_output=True, creationflags=creation_flags
            )
            msg_box.close()
            self.show_info_message("成功", f"{process_name}完成！\n文件已保存至:\n{output_file}")
        except FileNotFoundError:
            msg_box.close()
            self.show_error_message("错误", "找不到 'ffmpeg'。\n请确保已安装ffmpeg并将其添加至系统PATH。")
        except subprocess.CalledProcessError as e:
            msg_box.close()
            try:
                stderr_text = e.stderr.decode('utf-8')
            except UnicodeDecodeError:
                stderr_text = e.stderr.decode(sys.getdefaultencoding(), errors='ignore')
            self.show_error_message(f"FFmpeg {process_name}错误", f"FFmpeg在执行时返回错误:\n{stderr_text}")
        except Exception as e:
            msg_box.close()
            self.show_error_message("未知错误", f"发生了一个意外错误: {e}")

    def crop_video(self):
        if not self.input_file: return
        if self.start_time_sec >= self.end_time_sec:
            self.show_error_message("错误", "开始时间必须小于结束时间。")
            return

        start_time_fn = format_time(self.start_time_sec).replace(":", "-").replace(".", "_")
        end_time_fn = format_time(self.end_time_sec).replace(":", "-").replace(".", "_")
        path, filename = os.path.split(self.input_file)
        name, ext = os.path.splitext(filename)
        output_file = os.path.join(path, f"{name}_crop_{start_time_fn}_{end_time_fn}{ext}")

        command = [
            'ffmpeg', '-y',
            '-ss', str(self.start_time_sec),
            '-to', str(self.end_time_sec),
            '-i', self.input_file,
            '-c', 'copy', # Stream copy is fast, no re-encoding
            '-avoid_negative_ts', '1',
            output_file
        ]
        self._run_ffmpeg_command(command, output_file, "裁剪视频")

    # --- NEW: Audio Extraction Function ---
    def extract_audio(self):
        if not self.input_file: return
        if self.start_time_sec >= self.end_time_sec:
            self.show_error_message("错误", "开始时间必须小于结束时间。")
            return

        start_time_fn = format_time(self.start_time_sec).replace(":", "-").replace(".", "_")
        end_time_fn = format_time(self.end_time_sec).replace(":", "-").replace(".", "_")
        path, filename = os.path.split(self.input_file)
        name, _ = os.path.splitext(filename)
        # Output is always .mp3 as requested
        output_file = os.path.join(path, f"{name}_audio_{start_time_fn}_{end_time_fn}.mp3")

        # Command to re-encode audio to MP3. '-c:a copy' is not possible.
        command = [
            'ffmpeg', '-y',
            '-i', self.input_file,              # Input file
            '-ss', str(self.start_time_sec),    # Start time
            '-to', str(self.end_time_sec),      # End time
            '-vn',                              # vn = No Video
            '-c:a', 'libmp3lame',               # c:a = audio codec, re-encode to mp3
            '-q:a', '2',                        # q:a = audio quality, 2 is high quality VBR
            output_file
        ]
        self._run_ffmpeg_command(command, output_file, "提取音频")

    def show_error_message(self, title, text):
        QMessageBox.critical(self, title, text)
    def show_info_message(self, title, text):
        QMessageBox.information(self, title, text)
    def closeEvent(self, event):
        if self.player:
            self.player.quit()
        event.accept()

if __name__ == '__main__':
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    cropper = VideoCropper()
    cropper.show()
    sys.exit(app.exec_())