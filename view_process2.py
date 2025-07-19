import sys
import os
import subprocess
import shutil
from pathlib import Path
import datetime


# 设置环境变量，强制 Qt6 使用软件渲染后端 (Software Rasterizer)。
# 这是解决顽固的硬件加速兼容性问题的最可靠方法。
# 必须在 QApplication 实例化之前，甚至在导入 PyQt 模块之前完成。
os.environ["QSG_RHI_BACKEND"] = "software"
try:
    from natsort import natsorted
except ImportError:
    print("错误: 缺少 'natsort' 库。请通过 'pip install natsort' 命令安装后重试。")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QComboBox,
    QLabel, QCheckBox, QTextEdit, QListWidgetItem, QDialog, QSlider,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QProcess, QUrl
# 导入多媒体模块
try:
    from PyQt6.QtMultimedia import QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
except ImportError:
    print("错误: 缺少 PyQt6 多媒体模块。")
    print("请尝试运行 'pip install PyQt6-Multimedia' 和 'pip install PyQt6-MultimediaWidgets'。")
    sys.exit(1)


# --- 新增：视频裁切对话框 ---
class VideoCropperDialog(QDialog):
    def __init__(self, video_path, fps, main_window_process_runner, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.fps = fps if fps > 0 else 30.0 # 提供一个默认值以防万一
        self.frame_duration_ms = 1000 / self.fps
        self.main_window_process_runner = main_window_process_runner

        self.start_time_ms = None
        self.end_time_ms = None

        self.setWindowTitle("视频裁切")
        self.setMinimumSize(800, 600)

        # UI 初始化
        self.init_ui()
        # 加载视频
        self.player.setSource(QUrl.fromLocalFile(self.video_path))
        
    def init_ui(self):
        layout = QVBoxLayout(self)

        # 视频播放器
        self.video_widget = QVideoWidget()
        self.player = QMediaPlayer()
        self.player.setVideoOutput(self.video_widget)

        layout.addWidget(self.video_widget)
        
        # 进度条
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
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

        # 连接信号与槽
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.mediaStatusChanged.connect(self.media_status_changed)

        self.set_start_button.clicked.connect(self.set_start_point)
        self.set_end_button.clicked.connect(self.set_end_point)
        self.crop_button.clicked.connect(self.run_crop)
        
    def format_ms(self, ms):
        """将毫秒转换为 HH:MM:SS.ms 格式的字符串"""
        if ms is None:
            return "00:00:00.000"
        td = datetime.timedelta(milliseconds=ms)
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = td.microseconds // 1000
        return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    def media_status_changed(self, status):
        # 视频加载完成后，播放并立即暂停以显示第一帧
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.player.play()
            self.player.pause()

    def position_changed(self, position):
        self.slider.setValue(position)
        self.current_time_label.setText(f"当前: {self.format_ms(position)}")

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):
        self.player.setPosition(position)

    def set_start_point(self):
        self.start_time_ms = self.player.position()
        self.start_time_label.setText(f"开始点: {self.format_ms(self.start_time_ms)}")
        self.start_time_label.setStyleSheet("color: green; font-weight: bold;")

    def set_end_point(self):
        self.end_time_ms = self.player.position()
        self.end_time_label.setText(f"结束点: {self.format_ms(self.end_time_ms)}")
        self.end_time_label.setStyleSheet("color: red; font-weight: bold;")

    def keyPressEvent(self, event):
        key = event.key()
        current_pos = self.player.position()
        
        if key == Qt.Key.Key_Right:
            new_pos = current_pos + self.frame_duration_ms
            self.player.setPosition(int(new_pos))
            self.player.play()
            self.player.pause()
        elif key == Qt.Key.Key_Left:
            new_pos = current_pos - self.frame_duration_ms
            self.player.setPosition(int(max(0, new_pos)))
            self.player.play()
            self.player.pause()
        else:
            super().keyPressEvent(event)

    def run_crop(self):
        if self.start_time_ms is None or self.end_time_ms is None:
            QMessageBox.warning(self, "错误", "请先设置开始点和结束点。")
            return
        if self.start_time_ms >= self.end_time_ms:
            QMessageBox.warning(self, "错误", "结束点必须在开始点之后。")
            return

        video_path_obj = Path(self.video_path)
        output_dir = video_path_obj.parent
        
        start_str = self.format_ms(self.start_time_ms).replace(":", "-")
        end_str = self.format_ms(self.end_time_ms).replace(":", "-")

        output_name = f"{video_path_obj.stem}_crop_{start_str}_{end_str}.mp4"
        output_path = output_dir / output_name

        start_ffmpeg = self.format_ms(self.start_time_ms)
        end_ffmpeg = self.format_ms(self.end_time_ms)

        command = [
            'ffmpeg',
            '-i', self.video_path,
            '-ss', start_ffmpeg,
            '-to', end_ffmpeg,
            '-c', 'copy', # 直接复制流，不转码
            '-y',
            str(output_path)
        ]
        
        # 使用主窗口的进程执行器
        success_message = f"视频裁切完成！文件保存在:\n{output_path}"
        self.main_window_process_runner(command, success_message)
        self.accept() # 关闭对话框


class VideoMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频工具集 (合并、提取、裁切)")
        self.setGeometry(100, 100, 800, 700)

        if not self.check_ffmpeg():
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

        # --- 功能区 ---
        actions_layout = QHBoxLayout()
        
        # 合并
        self.merge_button = QPushButton("合并视频 (多选)")
        self.merge_button.clicked.connect(self.merge_videos)
        
        # 音频
        self.export_audio_button = QPushButton("导出音频")
        self.export_audio_button.clicked.connect(self.export_audio)

        # 裁切 (新按钮)
        self.crop_button = QPushButton("视频裁切 (单选)")
        self.crop_button.clicked.connect(self.open_crop_window)
        
        actions_layout.addWidget(self.merge_button)
        actions_layout.addWidget(self.export_audio_button)
        actions_layout.addWidget(self.crop_button)
        actions_layout.addStretch()

        # --- 合并选项 ---
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
        self.update_ui_state() # 初始状态

    def check_ffmpeg(self):
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            return True
        else:
            QMessageBox.critical(self, "依赖错误", "未找到 FFmpeg 或 FFprobe！\n\n请确保您已安装 FFmpeg 并将其添加到了系统环境变量 (PATH) 中。")
            return False

    def select_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择视频文件", "", "视频文件 (*.mp4 *.mkv *.mov *.avi *.flv);;所有文件 (*)")
        if files:
            self.video_list_widget.addItems(files)
            self.sort_list()

    def remove_selected_video(self):
        selected_items = self.video_list_widget.selectedItems()
        if not selected_items: return
        for item in selected_items:
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
        is_single_video = (count == 1)
        is_multiple_videos = (count > 1)
        
        self.crop_button.setEnabled(is_single_video)
        self.merge_button.setEnabled(is_multiple_videos)
        self.merge_before_audio_checkbox.setVisible(is_multiple_videos)

    # --- 新增：打开裁切窗口的方法 ---
    def open_crop_window(self):
        videos = self.get_video_list()
        if len(videos) != 1:
            return # 按钮状态已经控制，但作为双重保险
        
        video_path = videos[0]
        fps = self.get_video_fps(video_path)
        if fps is None:
            QMessageBox.critical(self, "错误", f"无法获取视频 '{Path(video_path).name}' 的帧率信息(FPS)。\n请检查文件是否完好。")
            return

        # 创建并执行对话框
        dialog = VideoCropperDialog(video_path, fps, self.run_process, self)
        dialog.exec()

    # --- 新增：使用 ffprobe 获取 FPS 的辅助函数 ---
    def get_video_fps(self, video_path):
        try:
            command = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=r_frame_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            self.log(f"正在获取FPS: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            frame_rate_str = result.stdout.strip()
            
            # FPS可能是分数（如 "30/1"）或小数
            if '/' in frame_rate_str:
                num, den = map(int, frame_rate_str.split('/'))
                return num / den if den != 0 else 0
            else:
                return float(frame_rate_str)
        except (subprocess.CalledProcessError, ValueError, ZeroDivisionError) as e:
            self.log(f"获取FPS失败: {e}")
            error_output = e.stderr if hasattr(e, 'stderr') else str(e)
            self.log(f"FFprobe 错误信息: {error_output}")
            return None

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
            reply = QMessageBox.question(self, "文件已存在", f"文件 '{output_path.name}' 已存在。是否覆盖？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.log("操作取消。")
                return

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
            self.show_message("错误", "请至少选择一个视频文件。", QMessageBox.Icon.Warning)
            return

        if len(videos) == 1:
            self.extract_single_audio(videos[0])
        else:
            if self.merge_before_audio_checkbox.isChecked():
                self.show_message("提示", "请先点击“合并视频”按钮，然后对合并后的文件单独进行音频提取。", QMessageBox.Icon.Information)
            else:
                self.log(f"准备从 {len(videos)} 个文件中分别提取音频...")
                for video in videos:
                    self.extract_single_audio(video)
                self.log("所有音频提取任务已启动。")

    def extract_single_audio(self, video_path_str):
        video_path = Path(video_path_str)
        output_dir = video_path.parent
        output_name = f"{video_path.stem}_audio.mp3"
        output_path = output_dir / output_name

        if output_path.exists():
            reply = QMessageBox.question(self, "文件已存在", f"文件 '{output_path.name}' 已存在。是否覆盖？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.log("操作取消。")
                return
        
        command = ['ffmpeg', '-i', str(video_path), '-vn', '-c:a', 'libmp3lame', '-q:a', '2', '-y', str(output_path)]
        self.run_process(command, f"音频提取完成！文件保存在:\n{output_path}")

    def run_process(self, command, success_message, cleanup_file=None):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.show_message("请稍候", "另一个任务正在进行中，请等待其完成后再试。", QMessageBox.Icon.Warning)
            return

        self.log("="*50 + f"\n执行命令: {' '.join(command)}\n" + "="*50)
        self.process = QProcess()
        
        def on_finished(exit_code, exit_status):
            if cleanup_file and os.path.exists(cleanup_file):
                try:
                    os.remove(cleanup_file)
                    self.log(f"已清理临时文件: {cleanup_file}")
                except OSError as e:
                    self.log(f"清理临时文件失败: {e}")

            if exit_code == 0:
                self.log(f"\n任务成功完成！\n{'-'*20}")
                self.show_message("成功", success_message, QMessageBox.Icon.Information)
            else:
                error_output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
                self.log(f"\n任务失败！退出代码: {exit_code}\n{'-'*20}\nFFmpeg 错误信息:\n{error_output}")
                self.show_message("失败", f"操作失败，请查看日志获取详细信息。", QMessageBox.Icon.Critical)
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
            reply = QMessageBox.question(self, "确认退出", "一个任务正在运行中。确定要强制退出吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.process.kill(); event.accept()
            else:
                event.ignore()
        else:
            event.accept()
if __name__ == "__main__":
    # --- 这里是需要添加的关键代码 ---
    # 在创建主应用之前，设置一个应用程序属性。
    # AA_UseSoftwareOpenGL 告诉 Qt 使用软件实现的 OpenGL 渲染，
    # 这可以避免与原生显卡驱动（如DirectX）的兼容性问题。
    # 这是解决视频预览时硬件加速错误的最佳方法。
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    # --- 添加结束 ---

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    main_win = VideoMergerApp()
    main_win.show()
    sys.exit(app.exec())