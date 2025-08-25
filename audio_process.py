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

class AudioMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音频合并工具")
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
        self.select_button = QPushButton("1. 选择音频 (可多选)")
        self.select_button.clicked.connect(self.select_audios)
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self.remove_selected_audio)
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_list)

        top_button_layout.addWidget(self.select_button)
        top_button_layout.addWidget(self.remove_button)
        top_button_layout.addWidget(self.clear_button)
        top_button_layout.addStretch()

        # --- 音频列表区 ---
        self.audio_list_widget = QListWidget()
        self.audio_list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.audio_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.audio_list_widget.setStyleSheet("QListWidget::item { padding: 5px; }")

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

        # --- 音频处理区 ---
        process_layout = QHBoxLayout()
        self.merge_button = QPushButton("2. 合并音频")
        self.merge_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.merge_button.clicked.connect(self.merge_audios)
        
        process_layout.addWidget(QLabel("输出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp3", "wav", "flac", "ogg", "m4a"])
        self.format_combo.setCurrentText("mp3")
        process_layout.addWidget(self.format_combo)
        
        # 音量标准化选项
        self.normalize_checkbox = QCheckBox("音量标准化")
        self.normalize_checkbox.setChecked(True)
        process_layout.addWidget(self.normalize_checkbox)
        
        process_layout.addWidget(self.merge_button)
        process_layout.addStretch()
        
        # --- 日志输出区 ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("FFmpeg 执行日志和状态信息将显示在这里...")

        # 添加组件到主布局
        main_layout.addLayout(top_button_layout)
        main_layout.addWidget(QLabel("音频文件列表 (可拖拽排序):"))
        main_layout.addWidget(self.audio_list_widget)
        main_layout.addLayout(sort_layout)
        main_layout.addSpacing(20)
        main_layout.addLayout(process_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(QLabel("执行日志:"))
        main_layout.addWidget(self.log_output)

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

    def select_audios(self):
        """打开文件对话框选择音频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;所有文件 (*)"
        )
        if files:
            self.audio_list_widget.addItems(files)
            self.sort_list() # 添加后立即进行自然排序

    def remove_selected_audio(self):
        """移除列表中选中的项"""
        selected_items = self.audio_list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.audio_list_widget.takeItem(self.audio_list_widget.row(item))

    def clear_list(self):
        """清空整个列表"""
        self.audio_list_widget.clear()

    def sort_list(self, reverse=False):
        """对列表中的项进行自然排序"""
        items = [self.audio_list_widget.item(i).text() for i in range(self.audio_list_widget.count())]
        sorted_items = natsorted(items, reverse=reverse)
        self.audio_list_widget.clear()
        self.audio_list_widget.addItems(sorted_items)

    def get_audio_list(self):
        """从 QListWidget 获取音频路径列表"""
        return [self.audio_list_widget.item(i).text() for i in range(self.audio_list_widget.count())]

    def merge_audios(self):
        """合并音频的核心功能"""
        audios = self.get_audio_list()
        if len(audios) < 2:
            self.show_message("错误", "请至少选择两个音频文件进行合并。", QMessageBox.Icon.Warning)
            return

        first_audio_path = Path(audios[0])
        output_dir = first_audio_path.parent
        output_ext = self.format_combo.currentText()
        output_name = f"{first_audio_path.stem}_merged.{output_ext}"
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
        list_file_path = output_dir / "ffmpeg_audio_list.txt"
        try:
            with open(list_file_path, 'w', encoding='utf-8') as f:
                for audio in audios:
                    # 处理路径中的单引号，避免ffmpeg命令出错
                    processed_path = audio.replace("'", "'\\''")
                    f.write(f"file {processed_path}\n")

            # 构建 ffmpeg 命令
            # 构建 ffmpeg 命令
            command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',  # 允许不安全的路径（绝对路径）
                '-i', str(list_file_path),
            ]

            # 如果需要音量标准化，添加相关参数
            if self.normalize_checkbox.isChecked():
                command.extend([
                    '-filter:a', 'loudnorm=I=-16:LRA=11:TP=-1.5',
                ])

            # 添加编码器和输出参数
            # 根据输出格式设置正确的编码器
            output_ext = self.format_combo.currentText()
            if output_ext == 'mp3':
                command.extend(['-c:a', 'libmp3lame'])
            elif output_ext in ['wav', 'flac']:
                # 无损格式可以直接复制或使用对应编码器
                command.extend(['-c:a', 'copy'] if not self.normalize_checkbox.isChecked() else 
                                ['-c:a', output_ext])
            elif output_ext == 'ogg':
                command.extend(['-c:a', 'libvorbis'])
            elif output_ext == 'm4a':
                command.extend(['-c:a', 'aac'])

            # 最终输出参数
            command.extend([
                '-y',  # 覆盖输出文件
                str(output_path)
            ])
    

            self.run_process(command, f"合并完成！文件保存在:\n{output_path}", list_file_path)

        except Exception as e:
            self.show_message("错误", f"创建临时文件失败: {e}", QMessageBox.Icon.Critical)
            if list_file_path.exists():
                os.remove(list_file_path)

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
            self.process = None  # 重置 process

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
        self.log_output.ensureCursorVisible()  # 滚动到底部

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
    # 初始化应用程序
    app = QApplication(sys.argv)

    # 设置应用程序的全局样式为 'Fusion'
    app.setStyle('Fusion')

    # 创建并显示主窗口
    main_win = AudioMergerApp()
    main_win.show()

    # 运行应用程序的事件循环
    sys.exit(app.exec())
