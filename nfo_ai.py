import os
import sys
import re
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QTextEdit, QPushButton, QFileDialog, 
                            QMessageBox, QSpinBox, QCheckBox, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt

# 模拟chat函数
def chat(system_content, json_data):
    """模拟调用AI生成简介的函数"""
    try:
        # 从JSON数据中提取每集标题
        episodes = json_data.get('episodes', [])
        if not episodes:
            return "暂无剧情简介"
        
        # 简单生成一个简介（实际应用中这里会调用真正的AI接口）
        titles = [ep.get('title', '') for ep in episodes if ep.get('title')]
        if not titles:
            return "暂无剧情简介"
        
        # 提取关键信息生成简介
        first_title = titles[0]
        last_title = titles[-1]
        mid_title = titles[len(titles)//2] if len(titles) > 1 else first_title
        
        # 模拟AI生成的简介
        return f"剧集围绕一系列事件展开，从{first_title}开始，经历{mid_title}，最终在{last_title}中达到高潮。"
    except Exception as e:
        return f"生成简介时出错: {str(e)}"

class NFOGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFO文件生成器")
        self.setGeometry(100, 100, 800, 600)
        
        # 存储视频文件信息
        self.video_files = []
        self.selected_folder = ""
        
        # 创建中心部件和布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建表单布局
        self.create_form_layout()
        
        # 创建按钮区域
        self.create_button_layout()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
    def create_form_layout(self):
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        
        # 标题
        self.add_text_field(form_layout, "电视剧名称", "title")
        
        # 原名
        self.add_text_field(form_layout, "电视剧原名（如果有）", "originaltitle")
        
        # 剧情简介组
        plot_group = QGroupBox("剧情简介")
        plot_layout = QVBoxLayout()
        
        # 剧情简介文本框
        self.plot = QTextEdit()
        plot_layout.addWidget(self.plot)
        
        # AI生成复选框和按钮
        ai_layout = QHBoxLayout()
        self.ai_generate_checkbox = QCheckBox("使用AI生成简介")
        self.ai_generate_checkbox.stateChanged.connect(self.toggle_ai_generate)
        self.ai_generate_button = QPushButton("生成AI简介")
        self.ai_generate_button.clicked.connect(self.generate_ai_plot)
        self.ai_generate_button.setEnabled(False)
        
        ai_layout.addWidget(self.ai_generate_checkbox)
        ai_layout.addWidget(self.ai_generate_button)
        ai_layout.addStretch()
        
        plot_layout.addLayout(ai_layout)
        plot_group.setLayout(plot_layout)
        form_layout.addWidget(plot_group)
        
        # 季节
        self.add_spin_box(form_layout, "季数", "season", 1, 1, 100)
        
        # 集数
        self.add_spin_box(form_layout, "起始集数", "episode", 1, 1, 100)
        
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
    
    def create_button_layout(self):
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        
        self.folder_button = QPushButton("选择视频文件夹")
        self.folder_button.clicked.connect(self.select_folder)
        button_layout.addWidget(self.folder_button)
        
        self.generate_button = QPushButton("生成NFO文件")
        self.generate_button.clicked.connect(self.generate_nfo_files)
        self.generate_button.setEnabled(False)
        button_layout.addWidget(self.generate_button)
        
        self.main_layout.addWidget(button_widget)
    
    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择视频文件夹")
        if folder_path:
            self.selected_folder = folder_path
            self.load_video_files(folder_path)
            self.generate_button.setEnabled(True)
            self.ai_generate_button.setEnabled(bool(self.video_files))
    
    def load_video_files(self, folder_path):
        # 获取视频文件列表
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
        self.video_files = [f for f in os.listdir(folder_path) 
                          if os.path.isfile(os.path.join(folder_path, f)) 
                          and os.path.splitext(f)[1].lower() in video_extensions]
        
        if not self.video_files:
            QMessageBox.warning(self, "警告", "所选文件夹中没有找到视频文件!")
            self.statusBar().showMessage("未找到视频文件")
            return
        
        self.statusBar().showMessage(f"已加载 {len(self.video_files)} 个视频文件")
    
    def toggle_ai_generate(self, state):
        if state == Qt.Checked:
            self.plot.setReadOnly(True)
            self.ai_generate_button.setEnabled(bool(self.video_files))
        else:
            self.plot.setReadOnly(False)
            self.ai_generate_button.setEnabled(False)
    
    def generate_ai_plot(self):
        if not self.video_files:
            QMessageBox.warning(self, "警告", "请先选择包含视频文件的文件夹!")
            return
        
        # 从视频文件名中提取标题
        episodes = []
        current_episode = self.episode.value()
        
        for video_file in self.video_files:
            # 尝试从文件名中提取标题和集数
            title = self.extract_title(video_file)
            ep_num = self.extract_episode_number(video_file) or current_episode
            
            episodes.append({
                'title': title,
                'episode': ep_num
            })
            
            current_episode += 1
        
        # 准备JSON数据
        json_data = {
            'title': self.title.text(),
            'episodes': episodes
        }
        
        # 系统提示词
        system_content = "请为一部电视剧生成简介，要求简介在50字以内，需概括剧集主要内容和情节发展。"
        
        # 调用AI生成简介
        generated_plot = chat(system_content, json_data)
        
        # 填充到剧情简介文本框
        self.plot.setPlainText(generated_plot)
    
    def extract_title(self, filename):
        # 从文件名中提取标题（去除扩展名和常见标记）
        base_name = os.path.splitext(filename)[0]
        
        # 移除常见前缀标记
        patterns = [
            r'^\[.*?\]',    # 移除方括号内的内容
            r'^\(.*?\)',    # 移除圆括号内的内容
            r'^P\d+',       # 移除P+数字格式
            r'^第\d+集'      # 移除"第X集"格式
        ]
        
        for pattern in patterns:
            base_name = re.sub(pattern, '', base_name).strip()
        
        return base_name
    
    def extract_episode_number(self, filename):
        # 尝试从文件名中提取集数
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
    
    def generate_nfo_files(self):
        if not self.selected_folder or not self.video_files:
            QMessageBox.warning(self, "警告", "请先选择包含视频文件的文件夹!")
            return
        
        try:
            # 获取用户输入
            title = self.title.text()
            originaltitle = self.originaltitle.text()
            plot = self.plot.toPlainText()
            season = self.season.value()
            start_episode = self.episode.value()
            year = self.year.value()
            genre = self.genre.text()
            studio = self.studio.text()
            
            # 生成主TVShow NFO文件
            tvshow_nfo_path = os.path.join(self.selected_folder, "tvshow.nfo")
            with open(tvshow_nfo_path, 'w', encoding='utf-8') as f:
                f.write(self.generate_tvshow_nfo(title, originaltitle, plot, year, genre, studio))
            
            # 为每个视频文件生成剧集NFO文件
            current_episode = start_episode
            for video_file in self.video_files:
                # 尝试从文件名中提取集数
                ep_num = self.extract_episode_number(video_file) or current_episode
                
                # 创建剧集NFO文件
                base_name = os.path.splitext(video_file)[0]
                episode_nfo_path = os.path.join(self.selected_folder, f"{base_name}.nfo")
                with open(episode_nfo_path, 'w', encoding='utf-8') as f:
                    f.write(self.generate_episode_nfo(title, plot, season, ep_num, year))
                
                current_episode += 1
            
            QMessageBox.information(self, "成功", f"已成功生成 {len(self.video_files) + 1} 个NFO文件!")
            self.statusBar().showMessage(f"已为 {len(self.video_files)} 个视频文件生成NFO文件")
            
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
    
    def generate_episode_nfo(self, title, plot, season, episode, year):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
    <title>{title} - 第{season}季 第{episode}集</title>
    <showtitle>{title}</showtitle>
    <plot>{plot}</plot>
    <season>{season}</season>
    <episode>{episode}</episode>
    <year>{year}</year>
</episodedetails>"""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NFOGenerator()
    window.show()
    sys.exit(app.exec_())    