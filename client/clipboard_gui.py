import sys
import pyperclip
import pyautogui
import time
import keyboard
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextEdit, QStatusBar, QMessageBox, QShortcut, QInputDialog, QDialog, QSpinBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot
from PyQt5.QtGui import QKeySequence
from clipboard_client import ClipboardSyncClient

class ClipboardGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = ClipboardSyncClient()
        # 将GUI实例传递给client，以便client可以调用GUI的模拟输入方法
        self.client.gui = self
        
        # 初始化快捷键设置（避免需要先打开设置才能使用快捷键）
        self.paste_shortcut_text = "Alt+V"
        self.simulate_shortcut_text = "Ctrl+Shift+T"
        self.stop_shortcut_text = "Ctrl+Shift+S"
        
        self.init_ui()
        self.setup_timer()
        self.setup_shortcuts()
        # 初始化时加载并应用设置
        if hasattr(self.client, 'typing_speed'):
            self.sync_btn.setEnabled(True)
            self.update_status(f'已加载配置，用户名: {self.client.username}' if self.client.username else '未连接')
        
    def init_ui(self):
        self.setWindowTitle('剪贴板同步工具')
        self.setGeometry(100, 100, 500, 400)
        
        # 主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        layout = QVBoxLayout()
        
        # 登录/注册区域
        self.setup_auth_ui(layout)
        
        # 剪贴板内容显示
        self.clipboard_display = QTextEdit()
        self.clipboard_display.setReadOnly(True)
        layout.addWidget(QLabel('剪贴板内容:'))
        layout.addWidget(self.clipboard_display)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status('未连接')
        
        main_widget.setLayout(layout)
        
    def setup_auth_ui(self, layout):
        auth_layout = QVBoxLayout()
        
        # 服务器地址
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel('服务器地址:'))
        self.server_input = QLineEdit(self.client.server_url)
        server_layout.addWidget(self.server_input)
        auth_layout.addLayout(server_layout)
        
        # 用户名和密码
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel('用户名:'))
        self.username_input = QLineEdit()
        if self.client.username:
            self.username_input.setText(self.client.username)
        user_layout.addWidget(self.username_input)
        auth_layout.addLayout(user_layout)
        
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel('密码:'))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        if self.client.password:
            self.password_input.setText(self.client.password)
        pass_layout.addWidget(self.password_input)
        auth_layout.addLayout(pass_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.login_btn = QPushButton('登录')
        self.login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(self.login_btn)
        
        self.register_btn = QPushButton('注册')
        self.register_btn.clicked.connect(self.handle_register)
        button_layout.addWidget(self.register_btn)
        
        self.sync_btn = QPushButton('开始同步')
        self.sync_btn.clicked.connect(self.toggle_sync)
        self.sync_btn.setEnabled(False)
        button_layout.addWidget(self.sync_btn)
        
        # 添加设置按钮
        self.settings_btn = QPushButton('设置')
        self.settings_btn.clicked.connect(self.open_settings)
        button_layout.addWidget(self.settings_btn)
        
        # 添加停止模拟输入按钮
        self.stop_typing_btn = QPushButton('停止模拟输入')
        self.stop_typing_btn.clicked.connect(self.stop_simulate_typing)
        self.stop_typing_btn.setEnabled(False)
        button_layout.addWidget(self.stop_typing_btn)
        
        auth_layout.addLayout(button_layout)
        layout.addLayout(auth_layout)
    
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clipboard_display)
        self.timer.start(1000)  # 每秒更新一次
    
    def update_clipboard_display(self):
        current_content = pyperclip.paste()
        self.clipboard_display.setPlainText(current_content)
    
    def update_status(self, message):
        self.status_bar.showMessage(message)
    
    def handle_login(self):
        # 如果正在同步，先停止
        if self.client.running:
            self.client.stop()
            self.sync_btn.setText('开始同步')
            self.update_status('同步已停止')
        
        self.client.server_url = self.server_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, '错误', '请输入用户名和密码')
            return
        
        if self.client.login(username, password):
            QMessageBox.information(self, '成功', '登录成功')
            self.sync_btn.setEnabled(True)
            self.update_status(f'已登录为: {username}')
        else:
            QMessageBox.warning(self, '错误', '登录失败')
    
    def handle_register(self):
        self.client.server_url = self.server_input.text()
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, '错误', '请输入用户名和密码')
            return
        
        if self.client.register(username, password):
            QMessageBox.information(self, '成功', '注册成功，请登录')
        else:
            QMessageBox.warning(self, '错误', '注册失败')
    
    def toggle_sync(self):
        if not self.client.running:
            if self.client.start():
                self.sync_btn.setText('停止同步')
                self.update_status('正在同步剪贴板...')
        else:
            self.client.stop()
            self.sync_btn.setText('开始同步')
            self.update_status('同步已停止')
            
    def setup_shortcuts(self):
        """设置全局快捷键"""
        # 使用keyboard库实现全局快捷键
        try:
            # 先清除所有现有快捷键
            keyboard.unhook_all()
            
            # 添加快捷键
            keyboard.add_hotkey(self.paste_shortcut_text, self.paste_from_clipboard)
            keyboard.add_hotkey(self.simulate_shortcut_text, self.paste_from_clipboard)
            keyboard.add_hotkey(self.stop_shortcut_text, self.stop_simulate_typing)
            print(f"快捷键已设置: {self.paste_shortcut_text}, {self.simulate_shortcut_text}, {self.stop_shortcut_text}")
        except Exception as e:
            print(f"设置快捷键失败: {e}")
        
    def paste_from_clipboard(self):
        """模拟键盘输入粘贴剪贴板内容"""
        if not self.client.running:
            return
            
        clipboard_content = pyperclip.paste()
        if clipboard_content:
            self.simulate_typing(clipboard_content, self.client.typing_speed)
            
    def simulate_typing(self, content, speed=100):
        """执行模拟输入"""
        try:
            # 启用PyAutoGUI的失败保护
            pyautogui.FAILSAFE = True
            
            # 确保speed不为None且为正数
            if speed is None or speed <= 0:
                speed = 100
            
            # 重置keyboard监听状态
            keyboard.unhook_all()
            self.setup_shortcuts()
            
            # 添加1秒延迟确保有足够时间切换窗口
            time.sleep(1)
            
            # 直接使用PyAutoGUI模拟键盘输入
            pyautogui.write(content, interval=speed/1000.0)
            
            self.stop_typing_btn.setEnabled(True)
            
        except pyautogui.FailSafeException:
            pass
        except Exception as e:
            print(f"模拟输入异常: {str(e)}")
            
    def handle_simulate_typing(self, content, speed):
        """处理来自服务端的模拟输入指令"""
        # 在主线程中执行模拟输入
        try:
            # 显示通知
            self.update_status(f'正在执行模拟输入，速度: {speed}ms')
            
            # 执行模拟输入
            self.simulate_typing(content, speed)
            
            # 恢复状态
            self.update_status('模拟输入完成')
            
        except Exception as e:
            print(f"处理模拟输入失败: {str(e)}")
            self.update_status(f'模拟输入失败: {str(e)}')
                
    def stop_simulate_typing(self):
        """停止模拟输入"""
        if not self.client.running:
            QMessageBox.warning(self, '警告', '请先启动同步功能')
            return
            
        try:
            # 按下ESC键停止当前输入
            pyautogui.press('esc')
            QMessageBox.information(self, '成功', '模拟输入已停止')
            self.stop_typing_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.warning(self, '错误', f"停止模拟输入失败: {str(e)}")
            
    def open_settings(self):
        """打开设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle('设置')
        dialog.setFixedSize(400, 350)
        
        layout = QVBoxLayout()
        
        # 添加同步间隔设置
        sync_interval_layout = QHBoxLayout()
        sync_interval_layout.addWidget(QLabel('同步间隔(秒):'))
        self.sync_interval_input = QSpinBox()
        self.sync_interval_input.setRange(1, 60)
        self.sync_interval_input.setValue(2)
        sync_interval_layout.addWidget(self.sync_interval_input)
        layout.addLayout(sync_interval_layout)
        
        # 添加模拟输入速度设置
        typing_speed_layout = QHBoxLayout()
        typing_speed_layout.addWidget(QLabel('模拟输入速度(ms):'))
        self.typing_speed_input = QSpinBox()
        self.typing_speed_input.setRange(5, 1000)
        self.typing_speed_input.setValue(self.client.typing_speed)
        self.typing_speed_input.setSingleStep(10)
        typing_speed_layout.addWidget(self.typing_speed_input)
        layout.addLayout(typing_speed_layout)
        
        # 添加快捷键设置
        shortcut_group = QWidget()
        shortcut_layout = QVBoxLayout()
        
        # 粘贴快捷键设置
        paste_shortcut_layout = QHBoxLayout()
        paste_shortcut_layout.addWidget(QLabel('粘贴快捷键:'))
        self.paste_shortcut_input = QLineEdit(self.paste_shortcut_text)
        paste_shortcut_layout.addWidget(self.paste_shortcut_input)
        shortcut_layout.addLayout(paste_shortcut_layout)
        
        # 模拟输入快捷键设置
        simulate_shortcut_layout = QHBoxLayout()
        simulate_shortcut_layout.addWidget(QLabel('模拟输入快捷键:'))
        self.simulate_shortcut_input = QLineEdit(self.simulate_shortcut_text)
        simulate_shortcut_layout.addWidget(self.simulate_shortcut_input)
        shortcut_layout.addLayout(simulate_shortcut_layout)
        
        # 停止模拟输入快捷键设置
        stop_shortcut_layout = QHBoxLayout()
        stop_shortcut_layout.addWidget(QLabel('停止模拟输入快捷键:'))
        self.stop_shortcut_input = QLineEdit(self.stop_shortcut_text)
        stop_shortcut_layout.addWidget(self.stop_shortcut_input)
        shortcut_layout.addLayout(stop_shortcut_layout)
        
        shortcut_group.setLayout(shortcut_layout)
        layout.addWidget(QLabel('快捷键设置:'))
        layout.addWidget(shortcut_group)
        
        # 添加保存按钮
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(lambda: self.save_settings(dialog))
        layout.addWidget(save_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
    def save_settings(self, dialog):
        """保存设置"""
        sync_interval = self.sync_interval_input.value()
        self.client.sync_interval = sync_interval
        self.timer.setInterval(sync_interval * 1000)
        
        # 保存模拟输入速度设置
        self.client.typing_speed = self.typing_speed_input.value()
        self.client.save_config()
        
        # 保存快捷键设置
        self.paste_shortcut_text = self.paste_shortcut_input.text()
        self.simulate_shortcut_text = self.simulate_shortcut_input.text()
        self.stop_shortcut_text = self.stop_shortcut_input.text()
        
        # 重新设置快捷键
        self.setup_shortcuts()
        
        QMessageBox.information(self, '成功', '设置已保存')
        dialog.close()

def main():
    app = QApplication(sys.argv)
    gui = ClipboardGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()