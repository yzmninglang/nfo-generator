import os
import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QTextEdit, QPushButton, QFileDialog, 
                            QMessageBox, QSpinBox, QComboBox)
from PyQt5.QtCore import Qt

class NFOGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFO文件生成器")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中心部件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建表单布局
        self.create_form_layout()
        
        # 创建选择文件夹按钮
        self.folder_button = QPushButton("选择视频文件夹")
        self.folder_button.clicked.connect(self.select_folder)
        self.main_layout.addWidget(self.folder_button)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
    def create_form_layout(self):
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        
        # 标题
        self.add_text_field(form_layout, "电视剧名称", "title")
        
        # 原名
        self.add_text_field(form_layout, "电视剧原名（如果有）", "originaltitle")
        
        # 剧情简介
        self.add_text_edit(form_layout, "剧情简介", "plot")
        
        # 季节
        self.add_spin_box(form_layout, "季数", "season", 1, 1, 100)
        
        # 集数
        self.add_spin_box(form_layout, "集数", "episode", 1, 1, 100)
        
        # 年份
        self.add_spin_box(form_layout, "年份", "year", 2000, 1900, 2100)
        
        # 类型
        genre_layout = QHBoxLayout()
        genre_layout.addWidget(QLabel("类型:"))
        self.genre = QLineEdit("学习")
        genre_layout.addWidget(self.genre)
        genre_layout.addStretch()
        form_layout.addLayout(genre_layout)
        
        # 工作室
        self.add_text_field(form_layout, "制作公司", "studio", "lang")
        
        self.main_layout.addWidget(form_widget)
    
    def add_text_field(self, layout, label_text, attr_name, default_text=""):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(f"{label_text}:"))
        field = QLineEdit(default_text)
        setattr(self, attr_name, field)
        h_layout.addWidget(field)
        h_layout.addStretch()
        layout.addLayout(h_layout)
    
    def add_text_edit(self, layout, label_text, attr_name):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(f"{label_text}:"))
        text_edit = QTextEdit()
        setattr(self, attr_name, text_edit)
        h_layout.addWidget(text_edit)
        layout.addLayout(h_layout)
    
    def add_spin_box(self, layout, label_text, attr_name, default_value, min_value, max_value):
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel(f"{label_text}:"))
        spin_box = QSpinBox()
        spin_box.setRange(min_value, max_value)
        spin_box.setValue(default_value)
        setattr(self, attr_name, spin_box)
        h_layout.addWidget(spin_box)
        h_layout.addStretch()
        layout.addLayout(h_layout)
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择视频文件夹")
        if folder_path:
            self.generate_nfo_files(folder_path)
    
    def generate_nfo_files(self, folder_path):
        try:
            # 获取用户输入
            title = self.title.text()
            originaltitle = self.originaltitle.text()
            plot = self.plot.toPlainText()
            season = self.season.value()
            episode = self.episode.value()
            year = self.year.value()
            genre = self.genre.text()
            studio = self.studio.text()
            
            # 获取视频文件列表
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
            video_files = [f for f in os.listdir(folder_path) 
                          if os.path.isfile(os.path.join(folder_path, f)) 
                          and os.path.splitext(f)[1].lower() in video_extensions]
            
            if not video_files:
                QMessageBox.warning(self, "警告", "所选文件夹中没有找到视频文件!")
                return
            
            # 生成主TVShow NFO文件
            tvshow_nfo_path = os.path.join(folder_path, "tvshow.nfo")
            with open(tvshow_nfo_path, 'w', encoding='utf-8') as f:
                f.write(self.generate_tvshow_nfo(title, originaltitle, plot, year, genre, studio))
            
            # 为每个视频文件生成剧集NFO文件
            current_episode = episode
            # print(video_files)
            for video_file in video_files:
                video_file_title=video_file.split('.')[-2]
                # 尝试从文件名中提取集数
                ep_num = self.extract_episode_number(video_file)
                if ep_num:
                    current_episode = ep_num
                
                # 创建剧集NFO文件
                base_name = os.path.splitext(video_file)[0]
                episode_nfo_path = os.path.join(folder_path, f"{base_name}.nfo")
                with open(episode_nfo_path, 'w', encoding='utf-8') as f:
                    f.write(self.generate_episode_nfo(title, plot, season, current_episode, year,video_file_title))
                
                current_episode += 1
            
            QMessageBox.information(self, "成功", f"已成功生成 {len(video_files) + 1} 个NFO文件!")
            self.statusBar().showMessage(f"已为 {len(video_files)} 个视频文件生成NFO文件")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成NFO文件时出错: {str(e)}")
            self.statusBar().showMessage(f"错误: {str(e)}")
    
    def generate_tvshow_nfo(self, title, originaltitle, plot, year, genre, studio):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
    <title>{title}</title>
    <originaltitle>{originaltitle}</originaltitle>
    <plot>{plot}</plot>
    <year>{year}</year>
    <genre>{genre}</genre>
    <studio>{studio}</studio>
</tvshow>"""
    
    def generate_episode_nfo(self, title, plot, season, episode, year,file_title):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
    <title>{episode}. {file_title}</title>
    <showtitle>{title}</showtitle>
    <plot>{plot}</plot>
    <season>{season}</season>
    <episode>{episode}</episode>
    <year>{year}</year>
</episodedetails>"""
    
    def extract_episode_number(self, filename):
        # 尝试从文件名中提取集数
        # 匹配常见格式如 [P01], E01, 第1集等
        patterns = [
            r'\[P(\d+)\]',    # 匹配 [P01] 格式
            r'E(\d+)',        # 匹配 E01 格式
            r'第(\d+)集'      # 匹配 第1集 格式
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NFOGenerator()
    window.show()
    sys.exit(app.exec_())    