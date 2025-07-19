import sys
import os
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QMessageBox,
    QComboBox,
)
from PyQt5.QtCore import QProcess, Qt
from PyQt5.QtGui import QTextCursor # <--- 在这里添加了缺失的导入

class SimplifiedMerger(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_files = {} # 用字典存储识别出的文件路径
        self.initUI()
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

    def initUI(self):
        self.setWindowTitle("视频合并工具 (简化版)")
        self.setGeometry(300, 300, 600, 450)

        vbox = QVBoxLayout()
        vbox.setSpacing(15)

        # 1. 文件选择区域
        select_hbox = QHBoxLayout()
        self.select_button = QPushButton("选择视频、音频、字幕文件...", self)
        self.select_button.setFixedHeight(40)
        self.select_button.clicked.connect(self.select_files)
        select_hbox.addWidget(self.select_button)
        vbox.addLayout(select_hbox)

        # 用于显示已选文件的标签
        self.files_display = QTextEdit(self)
        self.files_display.setReadOnly(True)
        self.files_display.setText("请点击上方按钮选择文件...")
        self.files_display.setFixedHeight(80)
        vbox.addWidget(self.files_display)

        # 2. 输出格式选择
        format_hbox = QHBoxLayout()
        format_label = QLabel("输出格式:", self)
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["mp4", "mkv"])
        format_hbox.addWidget(format_label)
        format_hbox.addWidget(self.format_combo)
        format_hbox.addStretch(1)
        vbox.addLayout(format_hbox)

        # 3. 合并按钮
        self.merge_button = QPushButton("开始合并", self)
        self.merge_button.setFixedHeight(40)
        self.merge_button.clicked.connect(self.merge_files)
        vbox.addWidget(self.merge_button)

        # 4. 输出日志控制台
        self.output_console = QTextEdit(self)
        self.output_console.setReadOnly(True)
        vbox.addWidget(self.output_console)

        self.setLayout(vbox)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择视频、音频和字幕文件", "", 
            "所有支持的文件 (*.mp4 *.mkv *.webm *.m4a *.aac *.mp3 *.srt *.ass *.vtt);;"
            "视频文件 (*.mp4 *.mkv *.webm);;"
            "音频文件 (*.m4a *.aac *.mp3);;"
            "字幕文件 (*.srt *.ass *.vtt)")
        
        if not files:
            return

        video_ext = ('.mp4', '.mkv', '.webm', '.avi')
        audio_ext = ('.m4a', '.aac', '.mp3', '.opus', '.wav')
        subtitle_ext = ('.srt', '.ass', '.vtt')
        
        self.selected_files = {} 
        
        for f in files:
            lower_f = f.lower()
            if lower_f.endswith(video_ext):
                self.selected_files['video'] = f
            elif lower_f.endswith(audio_ext):
                self.selected_files['audio'] = f
            elif lower_f.endswith(subtitle_ext):
                self.selected_files['subtitle'] = f
        
        display_text = (
            f"视频: {self.selected_files.get('video', '未选择')}\n"
            f"音频: {self.selected_files.get('audio', '未选择')}\n"
            f"字幕: {self.selected_files.get('subtitle', '未选择')}"
        )
        self.files_display.setText(display_text)

    def merge_files(self):
        if not all(k in self.selected_files for k in ['video', 'audio', 'subtitle']):
            QMessageBox.warning(self, "文件不完整", "请确保已同时选择一个视频、一个音频和一个字幕文件。")
            return

        video_file = self.selected_files['video']
        audio_file = self.selected_files['audio']
        subtitle_file = self.selected_files['subtitle']
        output_format = self.format_combo.currentText()

        video_path = Path(video_file)
        output_dir = video_path.parent
        output_basename = f"{video_path.stem}_merge"
        output_file = output_dir / f"{output_basename}.{output_format}"

        # 检查输出文件是否已存在，因为ffmpeg的 -y 参数会无提示覆盖，所以我们手动提示
        if output_file.exists():
            reply = QMessageBox.question(self, '文件已存在', 
                                         f"文件 '{output_file.name}' 已存在。要覆盖它吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.output_console.append(f"操作取消：用户选择不覆盖现有文件 '{output_file.name}'。")
                return

        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        except (subprocess.CalledProcessError, FileNotFoundError):
            QMessageBox.critical(self, "错误", "未找到 FFmpeg。请确保它已安装并位于系统的 PATH 中。")
            return

        self.merge_button.setEnabled(False)
        self.select_button.setEnabled(False)
        self.output_console.clear()
        
        # 基础命令和映射
        command = [
            "-i", video_file, "-i", audio_file, "-i", subtitle_file,
            "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0"
        ]

        if output_format == 'mkv':
            self.output_console.append("模式: 快速合并 (所有流直接复制)\n")
            command.extend(["-c", "copy"])
        else: # mp4
            self.output_console.append("模式: 兼容合并 (字幕将转码为 mov_text)\n")
            command.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text"])
        
        command.append(str(output_file))
        
        self.output_console.append(f"输出文件: {output_file}\n\n")
        
        # 使用 -y 自动覆盖，因为我们已经手动询问过用户了
        self.process.start("ffmpeg", ["-y"] + command)

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors='ignore')
        self.output_console.moveCursor(QTextCursor.End)
        self.output_console.insertPlainText(data)

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors='ignore')
        self.output_console.moveCursor(QTextCursor.End)
        self.output_console.insertPlainText(data)

    def process_finished(self):
        self.merge_button.setEnabled(True)
        self.select_button.setEnabled(True)
        if self.process.exitCode() == 0:
            self.output_console.append("\n合并成功！")
            QMessageBox.information(self, "成功", f"文件已成功合并！\n\n输出路径: {self.process.arguments()[-1]}")
        else:
            self.output_console.append("\n合并失败。")
            QMessageBox.critical(self, "错误", "合并过程中发生错误，请检查日志。")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ex = SimplifiedMerger()
    ex.show()
    sys.exit(app.exec_())