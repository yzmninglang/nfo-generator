# ==============================================================================
#  视频工具集 (合并、音频提取、裁切) - by Your AI Assistant
#
#  依赖:
#  - Python 库: PyQt6, natsort, python-mpv
#  - 外部程序 (需在系统PATH中): ffmpeg, ffprobe, mpv
# ==============================================================================
import sys
import os
import subprocess
import shutil
from pathlib import Path
import datetime

# 这行代码告诉程序，在寻找 .dll 文件时，也请在当前脚本所在的文件夹里找
# 这是解决 mpv.dll 找不到问题的代码层面的方案
os.environ['PATH'] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + os.environ['PATH']
# --- 修改结束 ---
# --- 依赖库导入与检查 ---
try:
    from natsort import natsorted
except ImportError:
    print("错误: 缺少 'natsort' 库。请通过 'pip install natsort' 命令安装后重试。")
    sys.exit(1)

try:
    import mpv
except ImportError:
    print("错误: 缺少 'python-mpv' 库。请通过 'pip install python-mpv' 命令安装后重试。")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QComboBox,
    QLabel, QCheckBox, QTextEdit, QListWidgetItem, QDialog, QSlider
)
from PyQt6.QtCore import Qt, QProcess, QUrl

# ==============================================================================
#  视频裁切对话框 (使用 MPV 播放器核心)
# ==============================================================================
class VideoCropperDialog(QDialog):
    def __init__(self, video_path, main_window_process_runner, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.main_window_process_runner = main_window_process_runner

        # 时间点以秒为单位
        self.start_time_sec = None
        self.end_time_sec = None
        
        self.setWindowTitle("视频裁切 (由 MPV 驱动)")
        self.setMinimumSize(800, 600)

        self.init_ui()
        self.init_mpv()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 1. 创建一个简单的 QWidget 作为 MPV 的渲染容器
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_container, 1)
        
        # 2. 进度条
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.seek_video)
        layout.addWidget(self.slider)

        # 时间标签布局
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("当前: 00:00:00.000")
        self.start_time_label = QLabel("开始点: (未设置)")
        self.end_time_label = QLabel("结束点: (未设置)")
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.start_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.end_time_label)
        layout.addLayout(time_layout)

        # 控制按钮布局
        control_layout = QHBoxLayout()
        self.set_start_button = QPushButton("设置为开始点")
        self.set_end_button = QPushButton("设置为结束点")
        self.crop_button = QPushButton("✅ 执行裁切")
        self.crop_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        control_layout.addWidget(self.set_start_button)
        control_layout.addWidget(self.set_end_button)
        control_layout.addStretch()
        control_layout.addWidget(self.crop_button)
        layout.addLayout(control_layout)

        self.set_start_button.clicked.connect(self.set_start_point)
        self.set_end_button.clicked.connect(self.set_end_point)
        self.crop_button.clicked.connect(self.run_crop)

    def init_mpv(self):
        # 将 MPV 渲染画面嵌入到 video_container 控件中
        # 使用 int() 而不是 str() 来获取窗口的数字ID
        container_id = int(self.video_container.winId()) # <--- 这是正确的做法
        self.player = mpv.MPV(
            wid=container_id,
            input_default_bindings=True,
            input_vo_keyboard=True,
            ytdl=False
        )
        
        # 观察 MPV 的属性变化，当变化时自动调用我们的函数
        self.player.observe_property('time-pos', self.on_time_pos_change)
        self.player.observe_property('duration', self.on_duration_change)

        self.player.play(self.video_path)
        self.player.pause = True

    def format_sec(self, seconds):
        if seconds is None: return "00:00:00.000"
        td = datetime.timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = td.microseconds // 1000
        return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    def on_time_pos_change(self, name, value):
        if value is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(int(value * 1000))
            self.slider.blockSignals(False)
            self.current_time_label.setText(f"当前: {self.format_sec(value)}")

    def on_duration_change(self, name, value):
        if value is not None:
            self.slider.setRange(0, int(value * 1000))

    def seek_video(self, position_ms):
        self.player.seek(position_ms / 1000, 'absolute')

    def set_start_point(self):
        self.start_time_sec = self.player.time_pos
        self.start_time_label.setText(f"开始点: {self.format_sec(self.start_time_sec)}")
        self.start_time_label.setStyleSheet("color: green; font-weight: bold;")

    def set_end_point(self):
        self.end_time_sec = self.player.time_pos
        self.end_time_label.setText(f"结束点: {self.format_sec(self.end_time_sec)}")
        self.end_time_label.setStyleSheet("color: red; font-weight: bold;")

    def keyPressEvent(self, event):
        key = event.key()
        # 使用 MPV 内置的帧步进命令，更精确
        if key == Qt.Key.Key_Right:
            self.player.frame_step()
        elif key == Qt.Key.Key_Left:
            self.player.frame_back()
        else:
            super().keyPressEvent(event)

    def run_crop(self):
        if self.start_time_sec is None or self.end_time_sec is None:
            QMessageBox.warning(self, "错误", "请先设置开始点和结束点。")
            return
        if self.start_time_sec >= self.end_time_sec:
            QMessageBox.warning(self, "错误", "结束点必须在开始点之后。")
            return

        video_path_obj = Path(self.video_path)
        output_dir = video_path_obj.parent
        start_str_file = self.format_sec(self.start_time_sec).replace(":", "-")
        end_str_file = self.format_sec(self.end_time_sec).replace(":", "-")
        output_name = f"{video_path_obj.stem}_crop_{start_str_file}_{end_str_file}.mp4"
        output_path = output_dir / output_name

        start_ffmpeg = self.format_sec(self.start_time_sec)
        end_ffmpeg = self.format_sec(self.end_time_sec)

        command = [
            'ffmpeg', '-i', self.video_path, '-ss', start_ffmpeg,
            '-to', end_ffmpeg, '-c', 'copy', '-y', str(output_path)
        ]
        
        self.main_window_process_runner(command, f"视频裁切完成！文件保存在:\n{output_path}")
        self.accept()

    def closeEvent(self, event):
        # 关闭对话框时，必须终止MPV进程以释放资源
        self.player.terminate()
        super().closeEvent(event)

# ==============================================================================
#  主应用程序窗口
# ==============================================================================
class VideoMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频工具集 (合并、提取、裁切)")
        self.setGeometry(100, 100, 800, 700)

        if not self.check_dependencies():
            sys.exit(1)

        self.init_ui()
        self.process = None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_button_layout = QHBoxLayout()
        self.select_button = QPushButton("1. 选择视频")
        self.select_button.clicked.connect(self.select_videos)
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self.remove_selected_video)
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)

        top_button_layout.addWidget(self.select_button)
        top_button_layout.addWidget(self.remove_button)
        top_button_layout.addWidget(self.clear_button)
        top_button_layout.addStretch()

        self.video_list_widget = QListWidget()
        self.video_list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.video_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.video_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }")

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("列表排序:"))
        self.sort_asc_button = QPushButton("正序 (默认)")
        self.sort_asc_button.clicked.connect(lambda: self.sort_list(reverse=False))
        self.sort_desc_button = QPushButton("逆序")
        self.sort_desc_button.clicked.connect(lambda: self.sort_list(reverse=True))
        sort_layout.addWidget(self.sort_asc_button)
        sort_layout.addWidget(self.sort_desc_button)
        sort_layout.addStretch()

        actions_layout = QHBoxLayout()
        self.merge_button = QPushButton("合并视频 (多选)")
        self.merge_button.clicked.connect(self.merge_videos)
        self.export_audio_button = QPushButton("导出音频")
        self.export_audio_button.clicked.connect(self.export_audio)
        self.crop_button = QPushButton("视频裁切 (单选)")
        self.crop_button.clicked.connect(self.open_crop_window)
        actions_layout.addWidget(self.merge_button)
        actions_layout.addWidget(self.export_audio_button)
        actions_layout.addWidget(self.crop_button)
        actions_layout.addStretch()

        merge_options_layout = QHBoxLayout()
        merge_options_layout.addWidget(QLabel("合并格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv"])
        merge_options_layout.addWidget(self.format_combo)
        self.merge_before_audio_checkbox = QCheckBox("先合并再导音频")
        merge_options_layout.addWidget(self.merge_before_audio_checkbox)
        merge_options_layout.addStretch()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("FFmpeg 执行日志和状态信息将显示在这里...")

        main_layout.addLayout(top_button_layout)
        main_layout.addWidget(QLabel("视频文件列表 (可拖拽排序):"))
        main_layout.addWidget(self.video_list_widget)
        main_layout.addLayout(sort_layout)
        main_layout.addSpacing(20)
        main_layout.addWidget(QLabel("功能操作:"))
        main_layout.addLayout(actions_layout)
        main_layout.addLayout(merge_options_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(QLabel("执行日志:"))
        main_layout.addWidget(self.log_output)
        
        self.video_list_widget.model().rowsInserted.connect(self.update_ui_state)
        self.video_list_widget.model().rowsRemoved.connect(self.update_ui_state)
        self.update_ui_state()

    def check_dependencies(self):
        missing = []
        if not shutil.which("ffmpeg"): missing.append("ffmpeg")
        if not shutil.which("ffprobe"): missing.append("ffprobe")
        if not shutil.which("mpv"): missing.append("mpv")
        
        if missing:
            QMessageBox.critical(self, "依赖错误", f"未找到以下必要组件: {', '.join(missing)}！\n\n请确保您已安装它们并将其添加到了系统环境变量 (PATH) 中。")
            return False
        return True

    def select_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择视频文件", "", "视频文件 (*.mp4 *.mkv *.mov *.avi *.flv);;所有文件 (*)")
        if files:
            self.video_list_widget.addItems(files)
            self.sort_list()

    def remove_selected_video(self):
        for item in self.video_list_widget.selectedItems():
            self.video_list_widget.takeItem(self.video_list_widget.row(item))

    def clear_list(self):
        self.video_list_widget.clear()

    def sort_list(self, reverse=False):
        items = self.get_video_list()
        sorted_items = natsorted(items, reverse=reverse)
        self.video_list_widget.clear()
        self.video_list_widget.addItems(sorted_items)

    def get_video_list(self):
        return [self.video_list_widget.item(i).text() for i in range(self.video_list_widget.count())]

    def update_ui_state(self):
        count = self.video_list_widget.count()
        self.crop_button.setEnabled(count == 1)
        self.merge_button.setEnabled(count > 1)
        self.merge_before_audio_checkbox.setVisible(count > 1)

    def open_crop_window(self):
        videos = self.get_video_list()
        if len(videos) != 1: return
        dialog = VideoCropperDialog(videos[0], self.run_process, self)
        dialog.exec()

    def merge_videos(self):
        videos = self.get_video_list()
        if len(videos) < 2:
            self.show_message("错误", "请至少选择两个视频文件进行合并。", QMessageBox.Icon.Warning)
            return

        first_video_path = Path(videos[0])
        output_dir = first_video_path.parent
        output_ext = self.format_combo.currentText()
        output_name = f"{first_video_path.stem}_merge.{output_ext}"
        output_path = output_dir / output_name

        if output_path.exists():
            if QMessageBox.question(self, "文件已存在", f"文件 '{output_path.name}' 已存在。是否覆盖？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                self.log("操作取消。"); return

        list_file_path = output_dir / "ffmpeg_list.txt"
        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for video in videos:
                    processed_path = video.replace("'", "'\\''")
                    f.write(f"file '{processed_path}'\n")
            command = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file_path), '-c', 'copy', '-y', str(output_path)]
            self.run_process(command, f"合并完成！文件保存在:\n{output_path}", list_file_path)
        except Exception as e:
            self.show_message("错误", f"创建临时文件失败: {e}", QMessageBox.Icon.Critical)
            if list_file_path.exists(): os.remove(list_file_path)
    
    def export_audio(self):
        videos = self.get_video_list()
        if not videos:
            self.show_message("错误", "请至少选择一个视频文件。", QMessageBox.Icon.Warning); return
        if len(videos) == 1:
            self.extract_single_audio(videos[0])
        else:
            if self.merge_before_audio_checkbox.isChecked():
                self.show_message("提示", "请先点击“合并视频”，然后对合并后的文件单独进行音频提取。", QMessageBox.Icon.Information)
            else:
                self.log(f"准备从 {len(videos)} 个文件中分别提取音频...")
                for video in videos: self.extract_single_audio(video)
                self.log("所有音频提取任务已启动。")

    def extract_single_audio(self, video_path_str):
        video_path = Path(video_path_str)
        output_path = video_path.with_name(f"{video_path.stem}_audio.mp3")
        if output_path.exists():
            if QMessageBox.question(self, "文件已存在", f"文件 '{output_path.name}' 已存在。是否覆盖？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                self.log("操作取消。"); return
        command = ['ffmpeg', '-i', str(video_path), '-vn', '-c:a', 'libmp3lame', '-q:a', '2', '-y', str(output_path)]
        self.run_process(command, f"音频提取完成！文件保存在:\n{output_path}")

    def run_process(self, command, success_message, cleanup_file=None):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.show_message("请稍候", "另一个任务正在进行中...", QMessageBox.Icon.Warning); return

        self.log("="*50 + f"\n执行命令: {' '.join(command)}\n" + "="*50)
        self.process = QProcess()
        
        def on_finished(exit_code, exit_status):
            if cleanup_file and os.path.exists(cleanup_file):
                try: os.remove(cleanup_file); self.log(f"已清理临时文件: {cleanup_file}")
                except OSError as e: self.log(f"清理临时文件失败: {e}")
            if exit_code == 0:
                self.log(f"\n任务成功完成！\n{'-'*20}")
                self.show_message("成功", success_message, QMessageBox.Icon.Information)
            else:
                error_output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
                self.log(f"\n任务失败！退出代码: {exit_code}\n{'-'*20}\nFFmpeg 错误信息:\n{error_output}")
                self.show_message("失败", "操作失败，请查看日志获取详细信息。", QMessageBox.Icon.Critical)
            self.process = None

        self.process.readyReadStandardOutput.connect(lambda: self.log(self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore').strip()))
        self.process.readyReadStandardError.connect(lambda: self.log(self.process.readAllStandardError().data().decode('utf-8', errors='ignore').strip()))
        self.process.finished.connect(on_finished)
        self.process.start(command[0], command[1:])

    def log(self, message):
        if message: self.log_output.append(message)
        self.log_output.ensureCursorVisible()

    def show_message(self, title, message, icon):
        msg_box = QMessageBox(self); msg_box.setWindowTitle(title); msg_box.setText(message); msg_box.setIcon(icon); msg_box.exec()

    def closeEvent(self, event):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            if QMessageBox.question(self, "确认退出", "一个任务正在运行中。确定要强制退出吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.process.kill(); event.accept()
            else:
                event.ignore()
        else:
            event.accept()

# ==============================================================================
#  程序入口
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    main_win = VideoMergerApp()
    main_win.show()
    sys.exit(app.exec())