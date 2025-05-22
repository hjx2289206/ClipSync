import pyperclip
import time
import requests
import json
import os
import sys
import threading
from datetime import datetime, timezone

class ClipboardSyncClient:
    def __init__(self, server_url="http://localhost:5000"):
        self.server_url = server_url
        self.last_clipboard = ""
        self.user_id = None
        self.username = None
        self.password = None
        self.session = requests.Session()
        self.sync_thread = None
        self.running = False
        self.config_file = "config.json"
        self.client_id = None
        self.typing_speed = 100  # 默认模拟输入速度为100ms
        self.processed_commands = set()  # 用于跟踪已处理的命令ID
        self.start_time = None  # 记录客户端启动时间
        self.load_config()

    def load_config(self):
        """从配置文件加载用户信息"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.username = config.get('username')
                    self.password = config.get('password')
                    self.server_url = config.get('server_url', self.server_url)
                    self.client_id = config.get('client_id')
                    self.typing_speed = config.get('typing_speed', 100)
                    print(f"已加载配置，用户名: {self.username}")
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save_config(self):
        """保存用户信息到配置文件"""
        config = {
            'username': self.username,
            'password': self.password,
            'server_url': self.server_url,
            'client_id': self.client_id,
            'typing_speed': self.typing_speed
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def login(self, username=None, password=None):
        """登录到服务器"""
        # 检查是否是切换账号
        is_account_change = False
        if username and username != self.username:
            is_account_change = True
            print(f"检测到账号切换: {self.username} -> {username}")
        
        if username:
            self.username = username
        if password:
            self.password = password

        if not self.username or not self.password:
            print("请提供用户名和密码")
            return False

        # 如果是切换账号或者没有客户端ID，生成新的客户端标识
        if not self.client_id or is_account_change:
            self.client_id = f"{self.username}-{os.getpid()}-{int(time.time())}"
            print(f"生成新的客户端ID: {self.client_id}")

        try:
            response = self.session.post(
                f"{self.server_url}/api/login",
                json={"username": self.username, "password": self.password, "client_id": self.client_id}
            )
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get('user_id')
                print(f"登录成功，用户ID: {self.user_id}")
                self.save_config()
                return True
            else:
                print(f"登录失败: {response.json().get('error')}")
                return False
        except Exception as e:
            print(f"登录请求失败: {e}")
            return False

    def register(self, username, password):
        """注册新用户"""
        try:
            response = requests.post(
                f"{self.server_url}/api/register",
                json={"username": username, "password": password}
            )
            if response.status_code == 201:
                print("注册成功，请登录")
                self.username = username
                self.password = password
                return True
            else:
                print(f"注册失败: {response.json().get('error')}")
                return False
        except Exception as e:
            print(f"注册请求失败: {e}")
            return False

    def sync_clipboard_to_server(self, content):
        """将剪贴板内容同步到服务器"""
        try:
            response = self.session.post(
                f"{self.server_url}/api/clipboard",
                json={"content": content, "content_type": "text"}
            )
            if response.status_code == 201:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 剪贴板内容已同步到服务器")
                return True
            else:
                print(f"同步失败: {response.json().get('error')}")
                return False
        except Exception as e:
            print(f"同步请求失败: {e}")
            return False

    def parse_timestamp(self, timestamp_str):
        """解析时间戳字符串为datetime对象"""
        try:
            print(f"[DEBUG] 原始时间戳: {timestamp_str}")
            
            # 尝试不同的时间戳格式
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO格式带毫秒和Z
                '%Y-%m-%dT%H:%M:%SZ',     # ISO格式不带毫秒和Z
                '%Y-%m-%dT%H:%M:%S.%f',   # ISO格式带毫秒不带Z
                '%Y-%m-%dT%H:%M:%S',      # ISO格式不带毫秒不带Z
                '%Y-%m-%d %H:%M:%S.%f',   # 标准格式带毫秒
                '%Y-%m-%d %H:%M:%S',      # 标准格式不带毫秒
            ]
            
            for fmt in formats:
                try:
                    if 'Z' in fmt:
                        # 如果格式包含Z，说明是UTC时间
                        dt = datetime.strptime(timestamp_str, fmt)
                        dt = dt.replace(tzinfo=timezone.utc)
                        local_dt = dt.astimezone()  # 转换为本地时区
                        print(f"[DEBUG] UTC时间转换为本地时间: {dt} -> {local_dt}")
                        return local_dt
                    else:
                        # 假设是本地时间
                        dt = datetime.strptime(timestamp_str, fmt)
                        print(f"[DEBUG] 解析为本地时间: {dt}")
                        return dt
                except ValueError:
                    continue
            
            # 如果所有格式都失败，尝试ISO解析
            try:
                if 'Z' in timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    local_dt = dt.astimezone()
                    print(f"[DEBUG] ISO解析UTC时间: {dt} -> {local_dt}")
                    return local_dt
                else:
                    dt = datetime.fromisoformat(timestamp_str)
                    print(f"[DEBUG] ISO解析本地时间: {dt}")
                    return dt
            except:
                pass
            
            print(f"[DEBUG] 所有解析方法都失败")
            return None
            
        except Exception as e:
            print(f"解析时间戳失败: {timestamp_str}, 错误: {e}")
            return None

    def get_latest_from_server(self):
        """从服务器获取最新的剪贴板内容"""
        try:
            response = self.session.get(f"{self.server_url}/api/clipboard/latest")
            if response.status_code == 200:
                data = response.json()
                content = data.get('content')
                content_type = data.get('content_type')
                timestamp_str = data.get('timestamp')
                
                # 检查是否是模拟输入指令
                if content_type == 'typing_command':
                    try:
                        command = json.loads(content)
                        if command.get('action') == 'simulate_typing':
                            command_id = command.get('command_id', 'unknown')
                            
                            # 检查是否已经处理过这个命令
                            if command_id in self.processed_commands:
                                return None  # 已处理过，忽略
                            
                            # 检查命令是否是在客户端启动之前创建的
                            if self.start_time and timestamp_str:
                                command_time = self.parse_timestamp(timestamp_str)
                                if command_time:
                                    # 确保两个时间都是同一时区的
                                    if command_time.tzinfo is None:
                                        # 如果命令时间没有时区信息，假设是UTC时间
                                        command_time = command_time.replace(tzinfo=timezone.utc).astimezone()
                                    
                                    start_time = self.start_time
                                    if start_time.tzinfo is None:
                                        # 如果启动时间没有时区信息，添加本地时区
                                        start_time = start_time.replace(tzinfo=datetime.now().astimezone().tzinfo)
                                    
                                    # 添加一些调试信息
                                    print(f"[DEBUG] 命令时间: {command_time}, 启动时间: {start_time}")
                                    
                                    # 如果命令时间早于客户端启动时间超过10秒，则认为是旧命令
                                    time_diff = (start_time - command_time).total_seconds()
                                    if time_diff > 10:
                                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 忽略启动前的旧命令: {command_id} (时间差: {time_diff:.2f}秒)")
                                        self.processed_commands.add(command_id)  # 标记为已处理
                                        return None
                                    else:
                                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 接受新命令: {command_id} (时间差: {time_diff:.2f}秒)")
                            
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收到模拟输入指令")
                            # 返回特殊格式以便在monitor_clipboard中处理
                            return {'type': 'typing_command', 'command': command}
                    except json.JSONDecodeError:
                        print("解析模拟输入指令失败")
                
                return content
            else:
                # 如果是404错误（没有剪贴板内容），不打印错误信息
                if response.status_code != 404:
                    print(f"获取最新内容失败: {response.json().get('error')}")
                return None
        except Exception as e:
            print(f"获取请求失败: {e}")
            return None

    def monitor_clipboard(self):
        """监控剪贴板变化并同步到服务器"""
        print("开始监控剪贴板...")
        self.last_clipboard = pyperclip.paste()
        connection_error_count = 0
        max_retry_count = 3
        
        while self.running:
            try:
                # 检查本地剪贴板是否有变化
                current_clipboard = pyperclip.paste()
                if current_clipboard != self.last_clipboard and current_clipboard.strip():
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检测到剪贴板变化")
                    self.last_clipboard = current_clipboard
                    if not self.sync_clipboard_to_server(current_clipboard):
                        print("同步到服务器失败，可能是网络连接问题")
                        connection_error_count += 1
                    else:
                        connection_error_count = 0  # 成功同步后重置错误计数
                
                # 检查服务器是否有新内容
                latest_content = self.get_latest_from_server()
                
                # 处理模拟输入指令
                if isinstance(latest_content, dict) and latest_content.get('type') == 'typing_command':
                    command = latest_content.get('command')
                    if command and 'content' in command:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 执行模拟输入指令")
                        self.execute_typing_command(command)
                        connection_error_count = 0
                # 处理普通剪贴板内容
                elif latest_content and latest_content != self.last_clipboard:
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 从服务器获取到新内容")
                    self.last_clipboard = latest_content
                    pyperclip.copy(latest_content)
                    connection_error_count = 0  # 成功获取后重置错误计数
                
                # 如果连续错误次数过多，尝试重新测试连接
                if connection_error_count >= max_retry_count:
                    print("检测到多次连接错误，正在尝试重新连接服务器...")
                    if self.test_server_connection():
                        print("服务器连接恢复正常")
                        connection_error_count = 0
                    else:
                        print("服务器连接仍然异常，将继续尝试")
                
                time.sleep(2)  # 每2秒检查一次
            except requests.exceptions.RequestException as e:
                print(f"网络请求错误: {e}")
                connection_error_count += 1
                time.sleep(5)  # 网络错误后等待5秒再继续
            except Exception as e:
                print(f"监控过程中出错: {e}")
                time.sleep(5)  # 出错后等待5秒再继续

    def test_server_connection(self):
        """测试与服务器的连接"""
        try:
            response = requests.get(f"{self.server_url}/api/ping", timeout=3)
            if response.status_code == 200:
                print(f"服务器连接成功: {self.server_url}")
                return True
            else:
                print(f"服务器连接失败，状态码: {response.status_code}，响应: {response.text if hasattr(response, 'text') else '无响应内容'}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"服务器连接错误: 无法连接到 {self.server_url}，请检查服务器地址是否正确或服务器是否已启动")
            return False
        except requests.exceptions.Timeout:
            print(f"服务器连接超时: {self.server_url} 响应超时，请检查网络连接")
            return False
        except requests.exceptions.RequestException as e:
            print(f"服务器连接错误: {e}")
            return False
    
    def start(self):
        """启动剪贴板同步"""
        # 先测试服务器连接
        if not self.test_server_connection():
            print("无法连接到服务器，请检查服务器地址和网络连接")
            return False
            
        if not self.user_id:
            if not self.login():
                return False
        
        if not self.running:
            self.running = True
            # 记录启动时间，用于忽略启动前的旧命令
            self.start_time = datetime.now()
            print(f"[DEBUG] 客户端启动时间: {self.start_time}")
            # 清空已处理的命令记录
            self.processed_commands.clear()
            self.sync_thread = threading.Thread(target=self.monitor_clipboard)
            self.sync_thread.daemon = True
            self.sync_thread.start()
            return True
        return False

    def execute_typing_command(self, command):
        """执行模拟输入指令"""
        try:
            content = command.get('content')
            typing_speed = command.get('typing_speed', self.typing_speed)
            command_id = command.get('command_id', 'unknown')
            
            # 记录这个命令已被处理
            self.processed_commands.add(command_id)
            
            # 清理旧的命令记录（保留最近100个）
            if len(self.processed_commands) > 100:
                # 转换为列表并保留最新的100个
                commands_list = list(self.processed_commands)
                self.processed_commands = set(commands_list[-100:])
            
            if not content:
                print("模拟输入内容为空")
                return
                
            print(f"开始执行模拟输入，命令ID: {command_id}")
            
            # 确保typing_speed不为None且为正数
            if typing_speed is None or typing_speed <= 0:
                typing_speed = self.typing_speed
            
            # 如果GUI界面存在，则调用其模拟输入方法
            if hasattr(self, 'gui') and self.gui:
                self.gui.handle_simulate_typing(content, typing_speed)
            else:
                # 直接执行模拟输入
                try:
                    import pyautogui
                    import time
                    
                    # 给用户一点时间切换到目标窗口
                    print("将在3秒后开始模拟输入，请切换到目标窗口...")
                    time.sleep(3)
                    
                    # 执行模拟输入
                    pyautogui.write(content, interval=typing_speed/1000.0)
                    print("模拟输入完成")
                except ImportError:
                    print("未安装pyautogui模块，无法执行模拟输入")
                except Exception as e:
                    print(f"模拟输入过程中出错: {e}")
        except Exception as e:
            print(f"执行模拟输入指令失败: {e}")
    
    def stop(self):
        """停止剪贴板同步"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
            print("剪贴板同步已停止")

def main():
    client = ClipboardSyncClient()
    
    # 简单的命令行界面
    if not client.username or not client.password:
        print("首次使用，请注册或登录")
        choice = input("1. 登录\n2. 注册\n请选择: ")
        
        if choice == "1":
            username = input("用户名: ")
            password = input("密码: ")
            if not client.login(username, password):
                return
        elif choice == "2":
            username = input("用户名: ")
            password = input("密码: ")
            if client.register(username, password):
                client.login(username, password)
            else:
                return
        else:
            print("无效选择")
            return
    
    print(f"已登录为: {client.username}")
    client.start()
    
    print("剪贴板同步客户端已启动，按Ctrl+C退出")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止服务...")
        client.stop()
        print("已退出")

if __name__ == "__main__":
    main()