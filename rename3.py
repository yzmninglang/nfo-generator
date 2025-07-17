import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QFileDialog, QListWidget, 
                            QLabel, QLineEdit, QSpinBox, QCheckBox, QMessageBox, 
                            QListWidgetItem, QDialog, QTextEdit)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QFont, QKeyEvent

# --- 全局辅助函数：自然排序 ---
def natural_sort_key(s):
    """
    为字符串提供自然排序的键。例如：'item2' 会在 'item10' 之前。
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'([0-9]+)', s)]

# ===================================================================
# == 新增：目录扁平化工具 对话框类
# ===================================================================
class FlattenToolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_dir = None
        self.rename_plan = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("目录扁平化工具")
        self.setMinimumSize(750, 550)
        self.main_layout = QVBoxLayout(self)

        # 1. 顶部选择区域
        top_layout = QHBoxLayout()
        self.select_dir_btn = QPushButton("选择要扁平化的根目录...")
        self.select_dir_btn.clicked.connect(self.select_root_dir)
        self.selected_dir_label = QLabel("未选择目录")
        self.selected_dir_label.setStyleSheet("color: grey;")
        top_layout.addWidget(self.select_dir_btn)
        top_layout.addWidget(self.selected_dir_label)
        top_layout.addStretch()
        self.main_layout.addLayout(top_layout)

        # 2. 预览区域
        preview_label = QLabel("预览 (原始路径 -> 新路径):")
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setFont(QFont("Consolas", 10))
        self.main_layout.addWidget(preview_label)
        self.main_layout.addWidget(self.preview_area)

        # 3. 底部按钮区域
        bottom_layout = QHBoxLayout()
        self.preview_btn = QPushButton("生成预览")
        self.preview_btn.clicked.connect(self.generate_preview)
        self.execute_btn = QPushButton("执行移动")
        self.execute_btn.clicked.connect(self.execute_move)
        self.execute_btn.setEnabled(False) # 默认禁用
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        
        bottom_layout.addWidget(self.preview_btn)
        bottom_layout.addWidget(self.execute_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(bottom_layout)

    def select_root_dir(self):
        folder = QFileDialog.getExistingDirectory(self, '选择要处理的根文件夹')
        if folder:
            self.root_dir = folder
            self.selected_dir_label.setText(f"已选择: {self.root_dir}")
            self.selected_dir_label.setStyleSheet("color: black;")
            self.preview_area.clear()
            self.execute_btn.setEnabled(False)
            self.rename_plan = []

    def generate_rename_plan(self):
        """核心逻辑：递归遍历目录，并生成重命名和移动计划。"""
        plan = []
        flatten_dir = os.path.join(self.root_dir, 'flatten')
        abs_flatten_dir = os.path.abspath(flatten_dir)

        def traverse(directory, parent_prefixes):
            try:
                items = os.listdir(directory)
            except OSError as e:
                self.preview_area.append(f"错误: 无法访问目录 {directory}: {e}")
                return

            # 过滤掉目标文件夹本身，防止无限递归
            items = [item for item in items if os.path.abspath(os.path.join(directory, item)) != abs_flatten_dir]
            
            dirs = sorted([d for d in items if os.path.isdir(os.path.join(directory, d))], key=natural_sort_key)
            files = sorted([f for f in items if os.path.isfile(os.path.join(directory, f))], key=natural_sort_key)
            
            # 先处理文件
            for file_index, filename in enumerate(files, 1):
                old_path = os.path.join(directory, filename)
                current_prefixes = parent_prefixes + [str(file_index)]
                prefix_str = ".".join(current_prefixes)
                new_filename = f"{prefix_str}.{filename}"
                plan.append({'old_path': old_path, 'new_filename': new_filename})

            # 再递归进入子目录
            for dir_index, dirname in enumerate(dirs, 1):
                path_to_recurse = os.path.join(directory, dirname)
                new_parent_prefixes = parent_prefixes + [str(dir_index)]
                traverse(path_to_recurse, new_parent_prefixes)

        # 从根目录开始遍历，初始前缀为空
        traverse(self.root_dir, [])
        return plan

    def generate_preview(self):
        if not self.root_dir:
            QMessageBox.warning(self, "警告", "请先选择一个根目录！")
            return
        
        self.preview_area.clear()
        self.execute_btn.setEnabled(False)
        QApplication.processEvents() # 刷新界面

        self.rename_plan = self.generate_rename_plan()

        if not self.rename_plan:
            self.preview_area.setText("在指定目录下没有找到任何文件。")
            return
        
        flatten_dir = os.path.join(self.root_dir, 'flatten')
        preview_lines = []
        preview_lines.append(f"总计 {len(self.rename_plan)} 个文件将被移动到 '{flatten_dir}' 目录中。\n" + "="*80)

        for item in self.rename_plan:
            destination_path = os.path.join(flatten_dir, item['new_filename'])
            preview_lines.append(f"源: {item['old_path']}\n → 新: {destination_path}\n")

        self.preview_area.setText("\n".join(preview_lines))
        self.execute_btn.setEnabled(True)

    def execute_move(self):
        if not self.rename_plan:
            QMessageBox.critical(self, "错误", "没有可执行的重命名计划。请先生成预览。")
            return

        reply = QMessageBox.question(self, '最终确认', 
                                     f'确定要移动 {len(self.rename_plan)} 个文件吗？\n\n'
                                     '此操作将从原始位置【移动】文件到新位置，操作不可撤销！',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        flatten_dir = os.path.join(self.root_dir, 'flatten')
        try:
            os.makedirs(flatten_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "创建目录失败", f"无法创建目标目录 '{flatten_dir}':\n{e}")
            return

        success_count = 0
        errors = []
        for item in self.rename_plan:
            old_path = item['old_path']
            destination_path = os.path.join(flatten_dir, item['new_filename'])
            try:
                os.rename(old_path, destination_path)
                success_count += 1
            except Exception as e:
                errors.append(f"移动失败: '{old_path}' ({e})")
        
        # 显示结果
        result_msg = f"操作完成！\n\n成功移动 {success_count} 个文件。"
        if errors:
            error_details = "\n".join(errors)
            QMessageBox.warning(self, '部分操作失败', f"{result_msg}\n\n遇到 {len(errors)} 个错误:\n{error_details}")
        else:
            QMessageBox.information(self, '操作成功', result_msg)
        
        # 重置状态
        self.preview_area.clear()
        self.execute_btn.setEnabled(False)
        self.rename_plan = []


# ===================================================================
# == 原有的批量重命名工具主窗口类 (有修改)
# ===================================================================
class DraggableListWidget(QListWidget):
    # (此部分代码未变，保持原样)
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
            mimeData.setText(str(self.row(item)))
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
            source_row = int(event.mimeData().text())
            target_item = self.itemAt(event.pos())
            target_row = self.row(target_item) if target_item else self.count()

            if source_row != target_row:
                dragged_item = self.takeItem(source_row)
                if source_row < target_row:
                    target_row -= 1
                self.insertItem(target_row, dragged_item)
                self.setCurrentItem(dragged_item)
                self.parent().sync_data_from_list_widget()
                
            event.accept()
            
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete:
            self.parent().remove_selected_files()
            return
        super().keyPressEvent(event)

class BatchRenamer(QMainWindow):
    # (此部分代码大部分未变，仅在 initUI 中添加一个按钮和方法)
    def __init__(self):
        super().__init__()
        self.file_data = []
        self.name_sort_asc = True
        self.time_sort_asc = True
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('批量文件重命名与扁平化工具')
        self.setGeometry(300, 300, 850, 650)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 文件选择区域
        file_select_layout = QHBoxLayout()
        self.select_files_btn = QPushButton('选择文件')
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_folder_btn = QPushButton('选择文件夹(非递归)')
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        # --- 新增：扁平化工具入口按钮 ---
        self.flatten_tool_btn = QPushButton('目录扁平化工具...')
        self.flatten_tool_btn.setStyleSheet("background-color: #D6EAF8;") # 给个醒目的颜色
        self.flatten_tool_btn.clicked.connect(self.open_flatten_tool)
        
        self.clear_files_btn = QPushButton('清空列表')
        self.clear_files_btn.clicked.connect(self.clear_files)
        
        file_select_layout.addWidget(self.select_files_btn)
        file_select_layout.addWidget(self.select_folder_btn)
        file_select_layout.addWidget(self.flatten_tool_btn) # 添加到布局
        file_select_layout.addWidget(self.clear_files_btn)
        main_layout.addLayout(file_select_layout)
        
        # (后续UI布局代码保持不变...为了简洁省略粘贴，请使用您上一版的代码)
        # 文件列表
        list_control_layout = QHBoxLayout()
        list_label = QLabel('文件列表 (可拖拽调整顺序, 按Delete键删除):')
        self.remove_files_btn = QPushButton('移除选中')
        self.remove_files_btn.clicked.connect(self.remove_selected_files)
        self.sort_name_btn = QPushButton('按名称排序(自然) ▲')
        self.sort_name_btn.clicked.connect(lambda: self.sort_files('name'))
        self.sort_time_btn = QPushButton('按修改时间排序 ▲')
        self.sort_time_btn.clicked.connect(lambda: self.sort_files('time'))
        list_control_layout.addWidget(list_label)
        list_control_layout.addStretch()
        list_control_layout.addWidget(self.remove_files_btn)
        list_control_layout.addWidget(self.sort_name_btn)
        list_control_layout.addWidget(self.sort_time_btn)
        main_layout.addLayout(list_control_layout)

        self.file_list = DraggableListWidget(self)
        self.file_list.setFont(QFont("Consolas", 12))
        main_layout.addWidget(self.file_list)
        
        # 重命名设置区域
        settings_group = QWidget()
        settings_layout = QVBoxLayout(settings_group)
        # ... (此处省略所有重命名设置UI，与上一版完全相同)
        prefix_layout = QHBoxLayout()
        prefix_label = QLabel('前缀:')
        self.prefix_input = QLineEdit()
        prefix_layout.addWidget(prefix_label)
        prefix_layout.addWidget(self.prefix_input)
        settings_layout.addLayout(prefix_layout)
        suffix_layout = QHBoxLayout()
        suffix_label = QLabel('后缀:')
        self.suffix_input = QLineEdit()
        suffix_layout.addWidget(suffix_label)
        suffix_layout.addWidget(self.suffix_input)
        settings_layout.addLayout(suffix_layout)
        remove_chars_layout = QHBoxLayout()
        remove_chars_label = QLabel('移除字符:')
        self.remove_chars_input = QLineEdit()
        self.remove_chars_input.setPlaceholderText('在此输入想从原文件名中删除的字符, 如: _-[]')
        remove_chars_layout.addWidget(remove_chars_label)
        remove_chars_layout.addWidget(self.remove_chars_input)
        settings_layout.addLayout(remove_chars_layout)
        regex_layout = QHBoxLayout()
        regex_label = QLabel('正则替换:')
        self.regex_pattern = QLineEdit()
        regex_pattern_label = QLabel('模式:')
        self.regex_replace = QLineEdit()
        regex_replace_label = QLabel('替换为:')
        self.regex_case = QCheckBox('区分大小写')
        self.regex_case.setChecked(True)
        regex_layout.addWidget(regex_label)
        regex_layout.addWidget(regex_pattern_label)
        regex_layout.addWidget(self.regex_pattern)
        regex_layout.addWidget(regex_replace_label)
        regex_layout.addWidget(self.regex_replace)
        regex_layout.addWidget(self.regex_case)
        settings_layout.addLayout(regex_layout)
        numbering_layout = QHBoxLayout()
        numbering_label = QLabel('序号设置:')
        self.numbering_char = QLineEdit('@')
        self.numbering_char.setMaximumWidth(30)
        numbering_char_label = QLabel('占位符:')
        self.number_length = QSpinBox()
        self.number_length.setRange(1, 10); self.number_length.setValue(2)
        number_length_label = QLabel('长度:')
        self.start_number = QSpinBox()
        self.start_number.setRange(0, 999999); self.start_number.setValue(1)
        start_number_label = QLabel('起始:')
        self.step_number = QSpinBox()
        self.step_number.setRange(1, 100); self.step_number.setValue(1)
        step_number_label = QLabel('步长:')
        numbering_layout.addWidget(numbering_label)
        numbering_layout.addWidget(numbering_char_label); numbering_layout.addWidget(self.numbering_char)
        numbering_layout.addWidget(number_length_label); numbering_layout.addWidget(self.number_length)
        numbering_layout.addWidget(start_number_label); numbering_layout.addWidget(self.start_number)
        numbering_layout.addWidget(step_number_label); numbering_layout.addWidget(self.step_number)
        numbering_layout.addStretch()
        settings_layout.addLayout(numbering_layout)
        
        main_layout.addWidget(settings_group)
        
        # 操作按钮区域
        buttons_layout = QHBoxLayout()
        options_layout = QHBoxLayout()
        self.keep_ext = QCheckBox('保留扩展名'); self.keep_ext.setChecked(True)
        options_layout.addWidget(self.keep_ext)
        options_layout.addStretch()
        self.preview_btn = QPushButton('预览重命名')
        self.preview_btn.clicked.connect(self.preview_rename)
        self.rename_btn = QPushButton('执行重命名')
        self.rename_btn.clicked.connect(self.perform_rename)
        self.rename_btn.setEnabled(False)
        buttons_layout.addLayout(options_layout)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.preview_btn)
        buttons_layout.addWidget(self.rename_btn)
        main_layout.addLayout(buttons_layout)
        
        self.statusBar().showMessage('就绪')

    # --- 新增：打开扁平化工具对话框的方法 ---
    def open_flatten_tool(self):
        """
        创建一个扁平化工具对话框实例并显示它。
        使用 exec_() 使其成为一个模态对话框，阻塞主窗口直到它关闭。
        """
        dialog = FlattenToolDialog(self)
        dialog.exec_()
    
    # (后续所有方法与上一版相同，无需修改... 为了简洁省略粘贴)
    def sync_data_from_list_widget(self):
        new_file_data = []
        current_names_in_data = {data[0]: data for data in self.file_data}
        for i in range(self.file_list.count()):
            name = self.file_list.item(i).text()
            if name in current_names_in_data:
                new_file_data.append(current_names_in_data[name])
        self.file_data = new_file_data
        self.statusBar().showMessage("文件顺序已更新")

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, '选择文件')
        if files: self.add_files(files)
            
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if folder:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            if files: self.add_files(files)
                
    def add_files(self, files):
        existing_paths = {data[1] for data in self.file_data}
        added_count = 0
        for file_path in files:
            if file_path not in existing_paths:
                file_name = os.path.basename(file_path)
                try: mtime = os.path.getmtime(file_path)
                except: mtime = 0
                self.file_data.append((file_name, file_path, mtime))
                self.file_list.addItem(file_name)
                added_count += 1
        if added_count > 0:
            self.statusBar().showMessage(f"已添加 {added_count} 个新文件，总计 {len(self.file_data)} 个文件")
        
    def clear_files(self):
        self.file_list.clear()
        self.file_data = []
        self.rename_btn.setEnabled(False)
        self.statusBar().showMessage('文件列表已清空')
        
    def sort_files(self, sort_type):
        if not self.file_data: return
            
        if sort_type == 'name':
            self.name_sort_asc = not self.name_sort_asc
            arrow = '▲' if self.name_sort_asc else '▼'
            self.sort_name_btn.setText(f'按名称排序(自然) {arrow}')
            self.file_data.sort(key=lambda x: natural_sort_key(x[0]), reverse=not self.name_sort_asc)
        elif sort_type == 'time':
            self.time_sort_asc = not self.time_sort_asc
            arrow = '▲' if self.time_sort_asc else '▼'
            self.sort_time_btn.setText(f'按修改时间排序 {arrow}')
            self.file_data.sort(key=lambda x: x[2], reverse=not self.time_sort_asc)
            
        self.file_list.clear()
        for file_name, _, _ in self.file_data:
            self.file_list.addItem(file_name)
        direction = "升序" if (self.name_sort_asc if sort_type == 'name' else self.time_sort_asc) else "降序"
        self.statusBar().showMessage(f"已按 {'名称' if sort_type == 'name' else '修改时间'} ({direction}) 排序")
        
    def remove_selected_files(self):
        selected_rows = sorted([self.file_list.row(item) for item in self.file_list.selectedItems()], reverse=True)
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要移除的文件")
            return
            
        for row in selected_rows:
            self.file_list.takeItem(row)
            if 0 <= row < len(self.file_data):
                del self.file_data[row]
                
        self.statusBar().showMessage(f"已移除 {len(selected_rows)} 个文件")
        if self.file_list.count() == 0: self.rename_btn.setEnabled(False)
            
    def _generate_new_name(self, original_name, current_number, settings):
        base_name, ext = os.path.splitext(original_name)
        new_base_name = base_name
        if settings['remove_chars']:
            for char_to_remove in settings['remove_chars']:
                new_base_name = new_base_name.replace(char_to_remove, '')
        if settings['regex']:
            new_base_name = settings['regex'].sub(settings['regex_replace'], new_base_name)
        number_str = str(current_number).zfill(settings['number_length'])
        new_name = settings['prefix'] + new_base_name + settings['suffix']
        new_name = new_name.replace(settings['number_char'], number_str)
        if settings['keep_ext']:
            new_name += ext
        return new_name

    def _get_settings(self):
        regex_pattern = self.regex_pattern.text()
        try:
            if regex_pattern:
                flags = 0 if self.regex_case.isChecked() else re.IGNORECASE
                regex = re.compile(regex_pattern, flags)
            else:
                regex = None
        except re.error as e:
            QMessageBox.critical(self, '正则表达式错误', f'无效的正则表达式: {str(e)}')
            return None
        return {
            "prefix": self.prefix_input.text(), "suffix": self.suffix_input.text(),
            "remove_chars": self.remove_chars_input.text(),
            "number_char": self.numbering_char.text() or '@',
            "number_length": self.number_length.value(), "start_number": self.start_number.value(),
            "step": self.step_number.value(), "regex": regex,
            "regex_replace": self.regex_replace.text(), "keep_ext": self.keep_ext.isChecked(),
        }

    def preview_rename(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, '警告', '文件列表为空！')
            return
        settings = self._get_settings()
        if not settings: return
        current_number = settings['start_number']
        preview_text = []
        self.sync_data_from_list_widget()
        for i in range(self.file_list.count()):
            original_name = self.file_data[i][0]
            new_name = self._generate_new_name(original_name, current_number, settings)
            preview_text.append(f"{original_name} → {new_name}")
            current_number += settings['step']
        dialog = QDialog(self)
        dialog.setWindowTitle('重命名预览'); dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit(dialog)
        text_edit.setReadOnly(True); text_edit.setFont(QFont("Consolas", 11))
        text_edit.setPlainText('\n'.join(preview_text))
        layout.addWidget(text_edit)
        ok_button = QPushButton('确定', dialog); ok_button.clicked.connect(dialog.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch(); button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
        dialog.exec_()
        self.rename_btn.setEnabled(True)
        self.statusBar().showMessage('已生成重命名预览，确认无误后可执行重命名')
        
    def perform_rename(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, '警告', '文件列表为空！')
            return
        reply = QMessageBox.question(self, '确认重命名', 
                                    '确定要执行重命名操作吗？\n此操作将直接修改硬盘上的文件名，且不可撤销！',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
        settings = self._get_settings()
        if not settings: return
        current_number = settings['start_number']
        renamed_count = 0; errors = []
        self.sync_data_from_list_widget()
        for i in range(len(self.file_data)):
            original_name, old_file_path, _ = self.file_data[i]
            file_dir = os.path.dirname(old_file_path)
            new_name = self._generate_new_name(original_name, current_number, settings)
            new_file_path = os.path.join(file_dir, new_name)
            if old_file_path != new_file_path:
                try:
                    os.rename(old_file_path, new_file_path)
                    renamed_count += 1
                    try: mtime = os.path.getmtime(new_file_path)
                    except: mtime = 0
                    self.file_data[i] = (new_name, new_file_path, mtime)
                    self.file_list.item(i).setText(new_name)
                except Exception as e:
                    errors.append(f"失败: {original_name} → {new_name} ({e})")
            current_number += settings['step']
        result_msg = f"成功重命名 {renamed_count} 个文件！"
        if errors:
            error_details = "\n".join(errors)
            QMessageBox.warning(self, '操作完成，但有错误', f"{result_msg}\n\n遇到 {len(errors)} 个错误:\n{error_details}")
        else:
            QMessageBox.information(self, '操作完成', result_msg)
        self.statusBar().showMessage(f"操作完成: 成功 {renamed_count} 个, 失败 {len(errors)} 个")
        self.rename_btn.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    default_font = QFont()
    default_font.setFamily(default_font.defaultFamily())
    default_font.setPointSize(10)
    app.setFont(default_font)
    
    renamer = BatchRenamer()
    renamer.show()
    sys.exit(app.exec_())