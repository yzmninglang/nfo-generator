import sys
import os
import subprocess
import shutil
from pathlib import Path

# 检查 natsort 是否安装
try:
    from natsort import natsorted
except ImportError:
    print("错误: 缺少 'natsort' 库。")
    print("请通过 'pip install natsort' 命令安装后重试。")
    sys.exit(1)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QMessageBox, QComboBox,
    QLabel, QCheckBox, QTextEdit, QListWidgetItem
)
from PyQt5.QtCore import Qt, QProcess

class VideoMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频合并与音频提取工具")
        self.setGeometry(100, 100, 800, 600)

        # 检查 ffmpeg 是否存在
        if not self.check_ffmpeg():
            sys.exit(1) # 如果 ffmpeg 不存在，则退出应用

        self.init_ui()
        self.process = None # 用于执行 ffmpeg 命令

    def init_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 顶部按钮区 ---
        top_button_layout = QHBoxLayout()
        self.select_button = QPushButton("1. 选择视频 (可多选)")
        self.select_button.clicked.connect(self.select_videos)
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self.remove_selected_video)
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)

        top_button_layout.addWidget(self.select_button)
        top_button_layout.addWidget(self.remove_button)
        top_button_layout.addWidget(self.clear_button)
        top_button_layout.addStretch()

        # --- 视频列表区 ---
        self.video_list_widget = QListWidget()
        self.video_list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.video_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.video_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }")

        # --- 排序按钮区 ---
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("列表排序:"))
        self.sort_asc_button = QPushButton("正序 (默认)")
        self.sort_asc_button.clicked.connect(lambda: self.sort_list(reverse=False))
        self.sort_desc_button = QPushButton("逆序")
        self.sort_desc_button.clicked.connect(lambda: self.sort_list(reverse=True))
        sort_layout.addWidget(self.sort_asc_button)
        sort_layout.addWidget(self.sort_desc_button)
        sort_layout.addStretch()

        # --- 合并功能区 ---
        merge_layout = QHBoxLayout()
        self.merge_button = QPushButton("2. 合并视频")
        self.merge_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.merge_button.clicked.connect(self.merge_videos)
        
        merge_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mkv"])
        merge_layout.addWidget(self.format_combo)
        merge_layout.addWidget(self.merge_button)
        merge_layout.addStretch()
        
        # --- 音频提取区 ---
        audio_layout = QHBoxLayout()
        self.export_audio_button = QPushButton("3. 导出音频 (mp3)")
        self.export_audio_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.export_audio_button.clicked.connect(self.export_audio)

        self.merge_before_audio_checkbox = QCheckBox("先合并再导出音频")
        self.merge_before_audio_checkbox.setChecked(True)
        self.merge_before_audio_checkbox.setVisible(False) # 默认隐藏

        audio_layout.addWidget(self.export_audio_button)
        audio_layout.addWidget(self.merge_before_audio_checkbox)
        audio_layout.addStretch()

        # --- 日志输出区 ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("FFmpeg 执行日志和状态信息将显示在这里...")

        # 添加组件到主布局
        main_layout.addLayout(top_button_layout)
        main_layout.addWidget(QLabel("视频文件列表 (可拖拽排序):"))
        main_layout.addWidget(self.video_list_widget)
        main_layout.addLayout(sort_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(merge_layout)
        main_layout.addSpacing(10)
        main_layout.addLayout(audio_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(QLabel("执行日志:"))
        main_layout.addWidget(self.log_output)
        
        # 监听列表变化，以更新复选框状态
        self.video_list_widget.model().rowsInserted.connect(self.update_ui_state)
        self.video_list_widget.model().rowsRemoved.connect(self.update_ui_state)

    def check_ffmpeg(self):
        """检查系统中是否安装了 ffmpeg 并可执行"""
        if shutil.which("ffmpeg"):
            return True
        else:
            QMessageBox.critical(
                self,
                "依赖错误",
                "未找到 FFmpeg！\n\n请确保您已安装 FFmpeg 并将其添加到了系统环境变量 (PATH) 中。",
                QMessageBox.StandardButton.Ok
            )
            return False

    def select_videos(self):
        """打开文件对话框选择视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.mkv *.mov *.avi *.flv);;所有文件 (*)"
        )
        if files:
            self.video_list_widget.addItems(files)
            self.sort_list() # 添加后立即进行自然排序

    def remove_selected_video(self):
        """移除列表中选中的项"""
        selected_items = self.video_list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.video_list_widget.takeItem(self.video_list_widget.row(item))

    def clear_list(self):
        """清空整个列表"""
        self.video_list_widget.clear()

    def sort_list(self, reverse=False):
        """对列表中的项进行自然排序"""
        items = [self.video_list_widget.item(i).text() for i in range(self.video_list_widget.count())]
        sorted_items = natsorted(items, reverse=reverse)
        self.video_list_widget.clear()
        self.video_list_widget.addItems(sorted_items)

    def get_video_list(self):
        """从 QListWidget 获取视频路径列表"""
        return [self.video_list_widget.item(i).text() for i in range(self.video_list_widget.count())]

    def update_ui_state(self):
        """根据视频列表数量更新UI组件的状态"""
        count = self.video_list_widget.count()
        # 只有多于一个视频时，音频合并复选框才可见
        self.merge_before_audio_checkbox.setVisible(count > 1)

    def merge_videos(self):
        """合并视频的核心功能"""
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
            reply = QMessageBox.question(
                self, "文件已存在", f"文件 '{output_path.name}' 已存在。是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.log("操作取消。")
                return

        # 创建一个临时文件列表供 ffmpeg concat 使用
        list_file_path = output_dir / "ffmpeg_list.txt"
        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for video in videos:
                    # --- 这里是修改的部分 ---
                    # 之前的代码在 f-string 内部使用了反斜杠，导致语法错误。
                    # 我们先处理好路径中的单引号，再将其放入 f-string。
                    # 这是为了处理文件名中可能包含单引号的情况，例如 "my's video.mp4"
                    processed_path = video.replace("'", "'\\''")
                    f.write(f"file {processed_path}\n")
                    # --- 修改结束 ---

            # 构建 ffmpeg 命令
            command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0', # 允许不安全的路径（绝对路径）
                '-i', str(list_file_path),
                '-c', 'copy', # 直接复制流，不重新编码
                '-y', # 覆盖输出文件
                str(output_path)
            ]
            self.run_process(command, f"合并完成！文件保存在:\n{output_path}", list_file_path)

        except Exception as e:
            self.show_message("错误", f"创建临时文件失败: {e}", QMessageBox.Icon.Critical)
            if list_file_path.exists():
                os.remove(list_file_path)

    def export_audio(self):
        """导出音频的核心功能"""
        videos = self.get_video_list()
        if not videos:
            self.show_message("错误", "请至少选择一个视频文件。", QMessageBox.Icon.Warning)
            return

        if len(videos) == 1:
            # 单个视频直接提取
            self.extract_single_audio(videos[0])
        else:
            # 多个视频根据复选框决定
            if self.merge_before_audio_checkbox.isChecked():
                self.merge_and_extract_audio()
            else:
                self.extract_multiple_audio_individually(videos)

    def extract_single_audio(self, video_path_str):
        """从单个视频中提取音频"""
        video_path = Path(video_path_str)
        output_dir = video_path.parent
        output_name = f"{video_path.stem}_audio.mp3"
        output_path = output_dir / output_name

        if output_path.exists():
            reply = QMessageBox.question(
                self, "文件已存在", f"文件 '{output_path.name}' 已存在。是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.log("操作取消。")
                return
        
        # --- 这里是修改的部分 ---
        # 原来的 '-c:a', 'copy' 无法将 aac 编码直接放入 mp3 容器。
        # 我们需要将其重新编码为 mp3。
        # 'libmp3lame' 是高质量的 mp3 编码器。
        # '-q:a 2' 是一个很好的可变比特率设置，能在保证高质量的同时控制文件大小。
        command = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',                 # 禁用视频流
            '-c:a', 'libmp3lame',  # <-- 这是修改的关键：指定使用 mp3 编码器
            '-q:a', '2',           # <-- 这是推荐的质量参数
            '-y',                  # 覆盖输出文件
            str(output_path)
        ]
        # --- 修改结束 ---
        
        self.run_process(command, f"音频提取完成！文件保存在:\n{output_path}")

    def merge_and_extract_audio(self):
        """先合并视频，然后从合并后的视频中提取音频"""
        self.log("功能开发提示：此功能需要先执行视频合并。请先点击“合并视频”按钮。")
        self.show_message("提示", "请先点击“合并视频”按钮生成合并后的文件，然后对该文件单独进行音频提取。", QMessageBox.Icon.Information)
        # 实际项目中，可以设计一个更复杂的流程，自动执行合并再提取，
        # 但为简化交互，引导用户分步操作更清晰。

    def extract_multiple_audio_individually(self, videos):
        """分别从多个视频中提取音频"""
        self.log(f"准备从 {len(videos)} 个文件中分别提取音频...")
        for video in videos:
            self.extract_single_audio(video)
        self.log("所有音频提取任务已启动。")
    
    def run_process(self, command, success_message, cleanup_file=None):
        """执行外部命令（如 ffmpeg）"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.show_message("请稍候", "另一个任务正在进行中，请等待其完成后再试。", QMessageBox.Icon.Warning)
            return

        self.log("="*50)
        self.log(f"执行命令: {' '.join(command)}")
        self.log("="*50)
        
        self.process = QProcess()
        
        # 定义完成后的操作
        def on_finished(exit_code, exit_status):
            # 清理临时文件
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
                self.log(f"\n任务失败！退出代码: {exit_code}\n{'-'*20}")
                self.log(f"FFmpeg 错误信息:\n{error_output}")
                self.show_message("失败", f"操作失败，请查看日志获取详细信息。", QMessageBox.Icon.Critical)
            self.process = None # 重置 process

        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(on_finished)

        self.process.start(command[0], command[1:])

    def handle_stdout(self):
        """处理标准输出"""
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        self.log(data.strip())

    def handle_stderr(self):
        """处理标准错误（ffmpeg 进度信息通常在这里）"""
        data = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
        self.log(data.strip())

    def log(self, message):
        """向日志文本框追加信息"""
        self.log_output.append(message)
        self.log_output.ensureCursorVisible() # 滚动到底部

    def show_message(self, title, message, icon):
        """显示一个简单的消息框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()

    def closeEvent(self, event):
        """关闭窗口时确认是否有进程在运行"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            reply = QMessageBox.question(
                self, "确认退出", "一个任务正在运行中。确定要强制退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.process.kill()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    # 1. 初始化应用程序
    app = QApplication(sys.argv)

    # 2. 设置应用程序的全局样式为 'Fusion'
    #    这会让所有窗口和控件都使用这种现代化的、跨平台的风格
    app.setStyle('Fusion')

    # 3. 创建并显示主窗口
    main_win = VideoMergerApp()
    main_win.show()

    # 4. 运行应用程序的事件循环
    sys.exit(app.exec())