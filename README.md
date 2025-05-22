# 剪贴板同步工具

这是一个跨设备的剪贴板同步工具，允许你在不同设备间同步和共享剪贴板内容。主要功能包括：

- 电脑端自动监控剪贴板变化并同步到服务器
- Web前端查看和管理剪贴板内容
- 支持从Web端添加内容并同步到电脑剪贴板
- 用户账号系统，确保数据安全和隐私

## 项目结构

```
剪贴板同步/
├── client/             # 客户端程序
│   ├── clipboard_client.py  # 剪贴板监控和同步客户端
│   └── requirements.txt     # 客户端依赖
├── server/             # 服务端程序
│   ├── app.py              # Flask服务端应用
│   ├── templates/          # 前端模板
│   │   └── index.html      # Web界面
│   └── requirements.txt    # 服务端依赖
└── README.md           # 项目说明文档
```

## 安装和使用

### 服务端设置

1. 进入服务端目录并安装依赖：

```bash
cd server
pip install -r requirements.txt
```

2. 启动服务端：

```bash
python app.py
```

服务端将在 http://localhost:5000 上运行。

### 客户端设置

1. 进入客户端目录并安装依赖：

```bash
cd client
pip install -r requirements.txt
```

2. 运行客户端：

```bash
python clipboard_client.py
```

3. 首次运行时，按照提示注册或登录账号。

## 使用方法

### Web端

1. 在浏览器中访问 http://localhost:5000
2. 注册新账号或登录已有账号
3. 在Web界面上可以：
   - 查看所有同步的剪贴板内容
   - 添加新内容到剪贴板
   - 复制或删除已有内容

### 客户端

1. 启动客户端并登录后，它会自动在后台运行
2. 当你复制内容到电脑剪贴板时，内容会自动同步到服务器
3. 当在Web端添加新内容时，内容会自动同步到电脑剪贴板

## 技术栈

- **客户端**：Python (pyperclip, requests)
- **服务端**：Flask, SQLAlchemy, SQLite
- **前端**：HTML, CSS, JavaScript

## 注意事项

- 默认情况下，服务端仅在本地网络运行。如需在公网访问，请适当配置网络和安全设置。
- 客户端和服务端需要网络连接才能正常同步。
- 目前仅支持文本内容的同步，未来可能会添加图片等多媒体内容支持。