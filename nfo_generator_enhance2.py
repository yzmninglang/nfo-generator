import os
import sys
import re
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QPushButton, QFileDialog,
                             QMessageBox, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt
from config import qwen_api
# AI 功能需要 openai 库, 如果你打算使用此功能,
# 请先通过命令行安装: pip install openai
try:
    import openai
except ImportError:
    # 允许在没有安装 openai 库的情况下运行程序，但AI功能将不可用
    openai = None

"""qwen_api = "sk-xxxxxxxx" """
global_api_key = qwen_api

class NFOGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFO 文件生成器 (增强版)")
        self.setGeometry(100, 100, 800, 700)
        
        # 创建中心部件和主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建表单布局
        self.create_form_layout()
        
        # 创建控制按钮和选项布局
        self.create_controls_layout()
        self.fold_path = None
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
    def create_form_layout(self):
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        
        self.add_text_field(form_layout, "电视剧名称", "title")
        self.add_text_field(form_layout, "电视剧原名（可选）", "originaltitle")
        self.add_text_edit(form_layout, "剧情简介", "plot")
        
        spin_boxes_layout = QHBoxLayout()
        self.add_spin_box(spin_boxes_layout, "季数", "season", 1, 1, 100)
        self.add_spin_box(spin_boxes_layout, "起始集数", "episode", 1, 1, 100)
        self.add_spin_box(spin_boxes_layout, "年份", "year", 2023, 1900, 2100)
        form_layout.addLayout(spin_boxes_layout)
        
        self.add_text_field(form_layout, "类型", "genre", "学习")
        self.add_text_field(form_layout, "制作公司", "studio", "lang")
        self.add_text_field(form_layout, "OpenAI API Key（可选）", "api_key")

        self.main_layout.addWidget(form_widget)

    def create_controls_layout(self):
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # 功能选项
        options_layout = QHBoxLayout()
        self.regenerate_all_checkbox = QCheckBox("为所有视频文件重新生成NFO")
        self.regenerate_all_checkbox.setChecked(False)
        self.regenerate_all_checkbox.setToolTip("如果不勾选，则只为没有NFO文件的视频生成")
        options_layout.addWidget(self.regenerate_all_checkbox)
        
        self.ai_generate_checkbox = QCheckBox("使用AI为每集生成简介")
        self.ai_generate_checkbox.setChecked(True)
        self.ai_generate_checkbox.setToolTip("需要提供有效的OpenAI API Key，并联网")
        options_layout.addWidget(self.ai_generate_checkbox)
        controls_layout.addLayout(options_layout)

        # 操作按钮
        buttons_layout = QHBoxLayout()
        self.load_nfo_button = QPushButton("加载 tvshow.nfo 信息")
        self.load_nfo_button.clicked.connect(self.load_tvshow_nfo_from_file)
        buttons_layout.addWidget(self.load_nfo_button)

        self.generate_button = QPushButton("选择文件夹并生成 NFO")
        self.generate_button.clicked.connect(self.select_folder_and_generate)
        buttons_layout.addWidget(self.generate_button)
        controls_layout.addLayout(buttons_layout)

        self.main_layout.addWidget(controls_widget)

    def add_text_field(self, layout, label_text, attr_name, default_text=""):
        h_layout = QHBoxLayout()
        label = QLabel(f"{label_text}:")
        label.setFixedWidth(150)
        h_layout.addWidget(label)
        field = QLineEdit(default_text)
        setattr(self, attr_name, field)
        h_layout.addWidget(field)
        layout.addLayout(h_layout)
    
    def add_text_edit(self, layout, label_text, attr_name):
        h_layout = QHBoxLayout()
        label = QLabel(f"{label_text}:")
        label.setFixedWidth(150)
        label.setAlignment(Qt.AlignTop)
        h_layout.addWidget(label)
        text_edit = QTextEdit()
        text_edit.setMinimumHeight(100)
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

    def load_tvshow_nfo_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件夹中的任意文件以加载tvshow.nfo")
        if not file_path:
            return
        
        folder_path = os.path.dirname(file_path)
        # print(folder_path)
        self.fold_path = folder_path
        tvshow_nfo_path = os.path.join(folder_path, "tvshow.nfo")

        if not os.path.exists(tvshow_nfo_path):
            QMessageBox.warning(self, "未找到文件", f"在目录 {folder_path} 中未找到 tvshow.nfo 文件。")
            return

        try:
            tree = ET.parse(tvshow_nfo_path)
            root = tree.getroot()
            
            self.title.setText(root.findtext('title', ''))
            self.originaltitle.setText(root.findtext('originaltitle', ''))
            self.plot.setPlainText(root.findtext('plot', ''))
            self.year.setValue(int(root.findtext('year', '2000')))
            self.genre.setText(root.findtext('genre', ''))
            self.studio.setText(root.findtext('studio', ''))
            
            QMessageBox.information(self, "成功", "已成功从 tvshow.nfo 加载信息。")
            self.statusBar().showMessage("tvshow.nfo 信息已加载")
        except ET.ParseError:
            QMessageBox.critical(self, "解析错误", "tvshow.nfo 文件格式错误，无法解析。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件时出错: {str(e)}")

    def detect_tvshow_file(self, tvshow_nfo_path):
        try:
            tree = ET.parse(tvshow_nfo_path)
            root = tree.getroot()
            
            self.title.setText(root.findtext('title', ''))
            self.originaltitle.setText(root.findtext('originaltitle', ''))
            self.plot.setPlainText(root.findtext('plot', ''))
            self.year.setValue(int(root.findtext('year', '2000')))
            self.genre.setText(root.findtext('genre', ''))
            self.studio.setText(root.findtext('studio', ''))
            
            # QMessageBox.information(self, "成功", "已成功从 tvshow.nfo 加载信息。")
        except:
            pass
    def select_folder_and_generate(self):
        if self.fold_path is  None:
            folder_path = QFileDialog.getExistingDirectory(self, "选择视频文件夹")
            self.detect_tvshow_file(os.path.join(folder_path, "tvshow.nfo"))
        else:
            folder_path = self.fold_path
        if folder_path:
            self.generate_nfo_files(folder_path)
    
    def generate_nfo_files(self, folder_path):
        try:
            # 获取用户输入
            title = self.title.text()
            originaltitle = self.originaltitle.text()
            plot = self.plot.toPlainText()
            season = self.season.value()
            episode_start = self.episode.value()
            year = self.year.value()
            genre = self.genre.text()
            studio = self.studio.text()
            
            # 检查AI选项
            use_ai = self.ai_generate_checkbox.isChecked()
            api_key = self.api_key.text()
            api_key = global_api_key
            if use_ai and (not openai or not api_key):
                QMessageBox.warning(self, "AI功能警告", "请勾选AI功能前，确保已安装'openai'库并填写了API Key。")
                return

            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']
            video_files = sorted([f for f in os.listdir(folder_path) 
                                if os.path.isfile(os.path.join(folder_path, f)) 
                                and os.path.splitext(f)[1].lower() in video_extensions])
            
            if not video_files:
                QMessageBox.warning(self, "警告", "所选文件夹中没有找到视频文件!")
                return
            
            tvshow_nfo_path = os.path.join(folder_path, "tvshow.nfo")
            with open(tvshow_nfo_path, 'w', encoding='utf-8') as f:
                f.write(self.generate_tvshow_nfo(title, originaltitle, plot, year, genre, studio))
            
            regenerate_all = self.regenerate_all_checkbox.isChecked()
            current_episode_counter = episode_start
            nfo_generated_count = 0
            
            # 初始化AI客户端（如果需要）
            ai_client = None
            if use_ai:
                try:
                    ai_client = openai.OpenAI(api_key=api_key,base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
                except Exception as e:
                    QMessageBox.critical(self, "AI 初始化失败", f"无法初始化OpenAI客户端: {e}")
                    return

            for video_file in video_files:
                base_name = os.path.splitext(video_file)[0]
                episode_nfo_path = os.path.join(folder_path, f"{base_name}.nfo")

                if not regenerate_all and os.path.exists(episode_nfo_path):
                    continue

                video_file_title = base_name
                try:
                    video_file_title = video_file_title.split(']')[-1].strip()
                    video_file_title = video_file_title.split('-')[-1].strip()
                except:
                    pass
                
                ep_num = self.extract_episode_number(video_file)
                if ep_num:
                    final_episode_num = ep_num
                else:
                    final_episode_num = current_episode_counter
                    current_episode_counter += 1

                episode_plot = plot
                if use_ai and ai_client:
                    self.statusBar().showMessage(f"正在为 '{video_file_title}' 生成AI简介...")
                    QApplication.processEvents()
                    try:
                        episode_plot = self.get_ai_generated_plot(ai_client, title, plot, video_file_title)
                        self.statusBar().showMessage(f"'{video_file_title}' 的AI简介已生成！")
                    except Exception as e:
                        QMessageBox.warning(self, "AI生成失败", f"为 {video_file_title} 生成简介失败: {e}\n将使用默认简介。")
                        self.statusBar().showMessage(f"AI简介生成失败，使用默认简介。")

                with open(episode_nfo_path, 'w', encoding='utf-8') as f:
                    f.write(self.generate_episode_nfo(title, episode_plot, season, final_episode_num, year, video_file_title))
                
                nfo_generated_count += 1
            
            QMessageBox.information(self, "成功", f"操作完成！\n总共生成了 {nfo_generated_count + 1} 个NFO文件 (包含tvshow.nfo)。")
            self.statusBar().showMessage(f"已为 {nfo_generated_count} 个视频文件生成了NFO")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成NFO文件时出错: {str(e)}")
            self.statusBar().showMessage(f"错误: {str(e)}")

    def get_ai_generated_plot(self, client, show_title, show_plot, episode_title):
        """
        使用新版 openai>1.0.0 的 API 调用方式
        """
        if not openai:
            raise ImportError("OpenAI library is not installed.")
        
        prompt = f"""
        你是一位专业的电视剧剧情摘要助手。
        请根据以下信息，为指定的一集生成一段引人入胜、简洁明了的剧情简介。

        电视剧名称: {show_title}
        电视剧主线剧情: {show_plot}
        本集标题: {episode_title}

        请只输出为 "{episode_title}" 这一集生成的剧情简介，不要包含“本集简介是：”或任何多余的客套话。
        """
        # client.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        # 新版 API 调用方式
        response = client.chat.completions.create(
            model="qwen3-235b-a22b",
            messages=[
                {"role": "system", "content": "你是一位专业的电视剧剧情摘要助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            extra_body={"enable_thinking": False},

        )
        
        # 新版获取返回内容的方式
        return response.choices[0].message.content.strip()

    def generate_tvshow_nfo(self, title, originaltitle, plot, year, genre, studio):
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
    <title>{title}</title>
    <originaltitle>{originaltitle}</originaltitle>
    <plot>{plot}</plot>
    <year>{year}</year>
    <genre>{genre}</genre>
    <studio>{studio}</studio>
</tvshow>"""
    
    def generate_episode_nfo(self, title, episode_plot, season, episode, year, file_title):
        file_title = file_title.replace('&', '-')
        file_title = re.sub(r'^\d+\s*[\.\-]?\s*', '', file_title)

        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<episodedetails>
    <title>{file_title}</title>
    <showtitle>{title}</showtitle>
    <season>{season}</season>
    <episode>{episode}</episode>
    <plot>{episode_plot}</plot>
    <year>{year}</year>
</episodedetails>"""
    
    def extract_episode_number(self, filename):
        patterns = [
            r'\[P(\d+)\]',            # 匹配 [P01] 格式
            r'[._ \-][Ee][Pp]?(\d+)', # E01, Ep01, ep01, -E01
            r'[Ss]\d+[Ee](\d+)',      # S01E01
            r'\[(\d+)\]',            # [01]
            r'第(\d+)[集话]',        # 第1集, 第1话
            r'^[^\w]*(\d+)[._ \-]'   # 01. xxx, 01-xxx, 01 xxx (在文件名开头)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    return int(match.groups()[-1])
                except (ValueError, IndexError):
                    continue
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NFOGenerator()
    window.show()
    sys.exit(app.exec_())