import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QListWidget, 
                            QLabel, QLineEdit, QSpinBox, QCheckBox, QMessageBox, 
                            QListWidgetItem, QInputDialog, QMenu, QAction)
from PyQt5.QtCore import Qt, QMimeData, QDateTime
from PyQt5.QtGui import QDrag, QFont, QKeyEvent

class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setAlternatingRowColors(True)
        
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            mimeData = QMimeData()
            mimeData.setText(item.text())
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.MoveAction)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        if event.mimeData().hasText():
            event.setDropAction(Qt.MoveAction)
            
            # 获取放下位置的行号
            row = self.row(self.itemAt(event.pos()))
            if row == -1:
                row = self.count()
                
            # 获取拖动的项目
            dragged_item = self.currentItem()
            if dragged_item:
                text = dragged_item.text()
                self.takeItem(self.row(dragged_item))
                new_item = QListWidgetItem(text)
                self.insertItem(row, new_item)
                self.setCurrentItem(new_item)
                
            event.accept()
            
    def keyPressEvent(self, event: QKeyEvent):
        # 处理Delete键
        if event.key() == Qt.Key_Delete:
            self.parent().remove_selected_files()
            return
        super().keyPressEvent(event)

class BatchRenamer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_data = []  # 存储文件名、路径和修改时间的元组列表
        self.name_sort_asc = True  # 名称排序默认正序
        self.time_sort_asc = True  # 时间排序默认正序
        self.initUI()
        
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('批量文件重命名工具')
        self.setGeometry(300, 300, 800, 600)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 文件选择区域
        file_select_layout = QHBoxLayout()
        self.select_files_btn = QPushButton('选择文件')
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn = QPushButton('选择文件夹')
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.clear_files_btn = QPushButton('清空文件')
        self.clear_files_btn.clicked.connect(self.clear_files)
        self.remove_files_btn = QPushButton('删除选中文件')
        self.remove_files_btn.clicked.connect(self.remove_selected_files)
        
        # 添加排序按钮
        self.sort_name_btn = QPushButton('按名称排序 ▲')
        self.sort_name_btn.clicked.connect(lambda: self.sort_files('name'))
        self.sort_time_btn = QPushButton('按修改时间排序 ▲')
        self.sort_time_btn.clicked.connect(lambda: self.sort_files('time'))
        
        file_select_layout.addWidget(self.select_files_btn)
        file_select_layout.addWidget(self.select_folder_btn)
        file_select_layout.addWidget(self.clear_files_btn)
        file_select_layout.addWidget(self.remove_files_btn)
        file_select_layout.addWidget(self.sort_name_btn)
        file_select_layout.addWidget(self.sort_time_btn)
        
        main_layout.addLayout(file_select_layout)
        
        # 文件列表区域
        list_label = QLabel('文件列表 (可拖拽调整顺序):')
        main_layout.addWidget(list_label)
        
        self.file_list = DraggableListWidget(self)
        # 设置字体大小
        font = self.file_list.font()
        font.setPointSize(12)
        self.file_list.setFont(font)
        main_layout.addWidget(self.file_list)
        
        # 重命名设置区域
        settings_group = QWidget()
        settings_layout = QVBoxLayout(settings_group)
        
        # 前缀设置
        prefix_layout = QHBoxLayout()
        prefix_label = QLabel('前缀:')
        # 增大字体
        prefix_label.setFont(QFont("SimHei", 12))
        self.prefix_input = QLineEdit()
        self.prefix_input.setFont(QFont("SimHei", 12))
        prefix_layout.addWidget(prefix_label)
        prefix_layout.addWidget(self.prefix_input)
        settings_layout.addLayout(prefix_layout)
        
        # 序号设置
        numbering_layout = QHBoxLayout()
        numbering_label = QLabel('序号设置:')
        numbering_label.setFont(QFont("SimHei", 12))
        self.numbering_char = QLineEdit('@')
        self.numbering_char.setFont(QFont("SimHei", 12))
        self.numbering_char.setMaximumWidth(30)
        numbering_char_label = QLabel('表示序号的特殊字符:')
        numbering_char_label.setFont(QFont("SimHei", 12))
        self.number_length = QSpinBox()
        self.number_length.setFont(QFont("SimHei", 12))
        self.number_length.setRange(1, 10)
        self.number_length.setValue(2)
        number_length_label = QLabel('序号长度:')
        number_length_label.setFont(QFont("SimHei", 12))
        self.start_number = QSpinBox()
        self.start_number.setFont(QFont("SimHei", 12))
        self.start_number.setRange(0, 999999)
        self.start_number.setValue(1)
        start_number_label = QLabel('起始序号:')
        start_number_label.setFont(QFont("SimHei", 12))
        self.step_number = QSpinBox()
        self.step_number.setFont(QFont("SimHei", 12))
        self.step_number.setRange(1, 100)
        self.step_number.setValue(1)
        step_number_label = QLabel('步长:')
        step_number_label.setFont(QFont("SimHei", 12))
        
        numbering_layout.addWidget(numbering_label)
        numbering_layout.addWidget(numbering_char_label)
        numbering_layout.addWidget(self.numbering_char)
        numbering_layout.addWidget(number_length_label)
        numbering_layout.addWidget(self.number_length)
        numbering_layout.addWidget(start_number_label)
        numbering_layout.addWidget(self.start_number)
        numbering_layout.addWidget(step_number_label)
        numbering_layout.addWidget(self.step_number)
        
        settings_layout.addLayout(numbering_layout)
        
        # 后缀设置
        suffix_layout = QHBoxLayout()
        suffix_label = QLabel('后缀:')
        suffix_label.setFont(QFont("SimHei", 12))
        self.suffix_input = QLineEdit()
        self.suffix_input.setFont(QFont("SimHei", 12))
        suffix_layout.addWidget(suffix_label)
        suffix_layout.addWidget(self.suffix_input)
        settings_layout.addLayout(suffix_layout)
        
        # 正则表达式替换设置
        regex_layout = QHBoxLayout()
        regex_label = QLabel('正则替换:')
        regex_label.setFont(QFont("SimHei", 12))
        self.regex_pattern = QLineEdit()
        self.regex_pattern.setFont(QFont("SimHei", 12))
        regex_pattern_label = QLabel('模式:')
        regex_pattern_label.setFont(QFont("SimHei", 12))
        self.regex_replace = QLineEdit()
        self.regex_replace.setFont(QFont("SimHei", 12))
        regex_replace_label = QLabel('替换为:')
        regex_replace_label.setFont(QFont("SimHei", 12))
        self.regex_case = QCheckBox('区分大小写')
        self.regex_case.setFont(QFont("SimHei", 12))
        self.regex_case.setChecked(True)
        
        regex_layout.addWidget(regex_label)
        regex_layout.addWidget(regex_pattern_label)
        regex_layout.addWidget(self.regex_pattern)
        regex_layout.addWidget(regex_replace_label)
        regex_layout.addWidget(self.regex_replace)
        regex_layout.addWidget(self.regex_case)
        
        settings_layout.addLayout(regex_layout)
        
        # 选项设置
        options_layout = QHBoxLayout()
        self.keep_ext = QCheckBox('保留扩展名')
        self.keep_ext.setFont(QFont("SimHei", 12))
        self.keep_ext.setChecked(True)
        self.preview_only = QCheckBox('仅预览')
        self.preview_only.setFont(QFont("SimHei", 12))
        self.preview_only.setChecked(True)
        
        options_layout.addWidget(self.keep_ext)
        options_layout.addWidget(self.preview_only)
        
        settings_layout.addLayout(options_layout)
        
        main_layout.addWidget(settings_group)
        
        # 操作按钮区域
        buttons_layout = QHBoxLayout()
        self.preview_btn = QPushButton('预览重命名')
        self.preview_btn.setFont(QFont("SimHei", 12))
        self.preview_btn.clicked.connect(self.preview_rename)
        self.rename_btn = QPushButton('执行重命名')
        self.rename_btn.setFont(QFont("SimHei", 12))
        self.rename_btn.clicked.connect(self.perform_rename)
        self.rename_btn.setEnabled(False)
        
        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addWidget(self.rename_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # 状态栏
        self.statusBar().showMessage('就绪')
        
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, '选择文件')
        if files:
            self.add_files(files)
            
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            files = [os.path.join(folder, f) for f in os.listdir(folder) 
                    if os.path.isfile(os.path.join(folder, f))]
            if files:
                self.add_files(files)
                
    def add_files(self, files):
        for file_path in files:
            file_name = os.path.basename(file_path)
            # 获取文件修改时间
            try:
                mtime = os.path.getmtime(file_path)
            except:
                mtime = 0
            # 存储文件名、路径和修改时间
            self.file_data.append((file_name, file_path, mtime))
            self.file_list.addItem(file_name)
        self.statusBar().showMessage(f"已添加 {len(files)} 个文件")
        
    def clear_files(self):
        self.file_list.clear()
        self.file_data = []
        self.rename_btn.setEnabled(False)
        self.statusBar().showMessage('文件列表已清空')
        
    def sort_files(self, sort_type):
        if not self.file_data:
            return
            
        if sort_type == 'name':
            # 切换名称排序方向
            self.name_sort_asc = not self.name_sort_asc
            # 更新按钮文本
            arrow = '▲' if self.name_sort_asc else '▼'
            self.sort_name_btn.setText(f'按名称排序 {arrow}')
            # 按文件名排序
            self.file_data.sort(key=lambda x: x[0].lower(), reverse=not self.name_sort_asc)
        elif sort_type == 'time':
            # 切换时间排序方向
            self.time_sort_asc = not self.time_sort_asc
            # 更新按钮文本
            arrow = '▲' if self.time_sort_asc else '▼'
            self.sort_time_btn.setText(f'按修改时间排序 {arrow}')
            # 按修改时间排序
            self.file_data.sort(key=lambda x: x[2], reverse=not self.time_sort_asc)
            
        # 更新文件列表显示
        self.file_list.clear()
        for file_name, _, _ in self.file_data:
            self.file_list.addItem(file_name)
            
        direction = "正序" if (self.name_sort_asc if sort_type == 'name' else self.time_sort_asc) else "逆序"
        self.statusBar().showMessage(f"已按{sort_type}({direction})排序")
        
    def remove_selected_files(self):
        # 获取选中的项目（按行号从大到小排序，避免删除后索引变化）
        selected_rows = sorted([self.file_list.row(item) for item in self.file_list.selectedItems()], reverse=True)
        
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要删除的文件")
            return
            
        # 从后往前删除，避免索引问题
        for row in selected_rows:
            self.file_list.takeItem(row)
            # 同步删除内存中的文件数据
            if 0 <= row < len(self.file_data):
                del self.file_data[row]
                
        count = len(selected_rows)
        self.statusBar().showMessage(f"已删除 {count} 个文件")
        
        # 如果文件列表为空，禁用重命名按钮
        if self.file_list.count() == 0:
            self.rename_btn.setEnabled(False)
            
    def preview_rename(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, '警告', '文件列表为空！')
            return
            
        # 获取设置
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()
        number_char = self.numbering_char.text()
        number_length = self.number_length.value()
        start_number = self.start_number.value()
        step = self.step_number.value()
        regex_pattern = self.regex_pattern.text()
        regex_replace = self.regex_replace.text()
        case_sensitive = self.regex_case.isChecked()
        keep_ext = self.keep_ext.isChecked()
        
        # 编译正则表达式
        try:
            if regex_pattern:
                if case_sensitive:
                    regex = re.compile(regex_pattern)
                else:
                    regex = re.compile(regex_pattern, re.IGNORECASE)
            else:
                regex = None
        except re.error as e:
            QMessageBox.critical(self, '正则表达式错误', f'无效的正则表达式: {str(e)}')
            return
            
        # 预览重命名
        current_number = start_number
        preview_text = []
        
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            original_name = item.text()
            # 获取对应的文件路径
            file_path = self.file_data[i][1]
            
            # 提取文件名和扩展名
            base_name, ext = os.path.splitext(original_name)
            
            # 应用正则表达式替换
            if regex:
                new_base_name = regex.sub(regex_replace, base_name)
            else:
                new_base_name = base_name
                
            # 替换特殊字符为序号
            number_str = str(current_number).zfill(number_length)
            new_name = prefix + new_base_name + suffix
            new_name = new_name.replace(number_char, number_str)
            
            # 添加扩展名
            if keep_ext:
                new_name += ext
                
            preview_text.append(f"{original_name} → {new_name}")
            current_number += step
            
        # 显示预览对话框
        preview_dialog = QMessageBox(self)
        preview_dialog.setWindowTitle('重命名预览')
        preview_dialog.setText('\n'.join(preview_text))
        preview_dialog.setStandardButtons(QMessageBox.Ok)
        preview_dialog.setDefaultButton(QMessageBox.Ok)
        
        if self.file_list.count() > 10:
            # 如果文件太多，使用滚动区域
            from PyQt5.QtWidgets import QTextEdit, QDialog
            dialog = QDialog(self)
            dialog.setWindowTitle('重命名预览')
            dialog.setMinimumSize(600, 400)
            layout = QVBoxLayout(dialog)
            text_edit = QTextEdit(dialog)
            text_edit.setReadOnly(True)
            text_edit.setPlainText('\n'.join(preview_text))
            layout.addWidget(text_edit)
            button_layout = QHBoxLayout()
            ok_button = QPushButton('确定', dialog)
            ok_button.clicked.connect(dialog.accept)
            button_layout.addStretch()
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            dialog.exec_()
        else:
            preview_dialog.exec_()
            
        self.rename_btn.setEnabled(True)
        self.statusBar().showMessage('已生成重命名预览')
        
    def perform_rename(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, '警告', '文件列表为空！')
            return
            
        if not self.preview_only.isChecked():
            reply = QMessageBox.question(self, '确认重命名', 
                                        '确定要执行重命名操作吗？此操作不可撤销！',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
                
        # 获取设置
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()
        number_char = self.numbering_char.text()
        number_length = self.number_length.value()
        start_number = self.start_number.value()
        step = self.step_number.value()
        regex_pattern = self.regex_pattern.text()
        regex_replace = self.regex_replace.text()
        case_sensitive = self.regex_case.isChecked()
        keep_ext = self.keep_ext.isChecked()
        preview_only = self.preview_only.isChecked()
        
        # 编译正则表达式
        try:
            if regex_pattern:
                if case_sensitive:
                    regex = re.compile(regex_pattern)
                else:
                    regex = re.compile(regex_pattern, re.IGNORECASE)
            else:
                regex = None
        except re.error as e:
            QMessageBox.critical(self, '正则表达式错误', f'无效的正则表达式: {str(e)}')
            return
            
        # 执行重命名
        current_number = start_number
        renamed_count = 0
        errors = []
        
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            original_name = item.text()
            # 获取对应的文件路径
            old_file_path = self.file_data[i][1]
            file_dir = os.path.dirname(old_file_path)
            
            # 提取文件名和扩展名
            base_name, ext = os.path.splitext(original_name)
            
            # 应用正则表达式替换
            if regex:
                new_base_name = regex.sub(regex_replace, base_name)
            else:
                new_base_name = base_name
                
            # 替换特殊字符为序号
            number_str = str(current_number).zfill(number_length)
            new_name = prefix + new_base_name + suffix
            new_name = new_name.replace(number_char, number_str)
            
            # 添加扩展名
            if keep_ext:
                new_name += ext
                
            new_file_path = os.path.join(file_dir, new_name)
            
            # 执行重命名（如果不是仅预览模式）
            if not preview_only:
                try:
                    os.rename(old_file_path, new_file_path)
                    renamed_count += 1
                    # 获取新文件的修改时间
                    try:
                        mtime = os.path.getmtime(new_file_path)
                    except:
                        mtime = 0
                    # 更新内存中的文件数据
                    self.file_data[i] = (new_name, new_file_path, mtime)
                    # 更新显示
                    item.setText(new_name)
                except Exception as e:
                    errors.append(f"无法重命名 {original_name}: {str(e)}")
                    
            current_number += step
            
        # 显示结果
        result_msg = f"重命名完成！"
        if preview_only:
            result_msg = "重命名预览完成！"
        else:
            result_msg = f"成功重命名 {renamed_count} 个文件！"
            
        if errors:
            result_msg += f"\n\n遇到 {len(errors)} 个错误:\n" + "\n".join(errors)
            
        QMessageBox.information(self, '操作完成', result_msg)
        self.statusBar().showMessage(result_msg)
        
        # 如果不是预览模式，禁用重命名按钮
        if not preview_only:
            self.rename_btn.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 确保中文显示正常
    font = QFont("SimHei", 12)  # 增大整体字体大小
    app.setFont(font)
    
    renamer = BatchRenamer()
    renamer.show()
    sys.exit(app.exec_())    