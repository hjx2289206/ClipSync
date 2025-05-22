from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import json
import threading
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clipboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db = SQLAlchemy(app)

# 使用本地时间而不是UTC时间
def get_current_time():
    return datetime.now()

# 添加ping接口用于连接测试
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok', 'message': '服务器正常运行中'}), 200

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    clips = db.relationship('ClipboardItem', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 剪贴板内容模型
class ClipboardItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.String(20), default='text')  # text, image, etc.
    timestamp = db.Column(db.DateTime, default=get_current_time)  # 使用本地时间
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# 客户端连接模型
class ClientConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_seen = db.Column(db.DateTime, default=get_current_time)  # 使用本地时间
    is_online = db.Column(db.Boolean, default=True)
    name = db.Column(db.String(100))  # 新增客户端名称字段
    
    user = db.relationship('User', backref=db.backref('clients', lazy=True))

# 创建数据库表
with app.app_context():
    db.create_all()

# 注册路由
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 400
    
    user = User(username=username)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': '注册成功'}), 201

# 登录路由
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    client_id = data.get('client_id')
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    session['user_id'] = user.id
    
    # 记录客户端连接
    if client_id:
        # 检查是否已存在该客户端记录
        client = ClientConnection.query.filter_by(client_id=client_id).first()
        if client:
            client.last_seen = get_current_time()
            client.is_online = True
        else:
            client = ClientConnection(client_id=client_id, user_id=user.id)
            db.session.add(client)
        db.session.commit()
    
    return jsonify({'message': '登录成功', 'user_id': user.id}), 200

# 添加剪贴板内容
@app.route('/api/clipboard', methods=['POST'])
def add_clipboard():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    data = request.get_json()
    content = data.get('content')
    content_type = data.get('content_type', 'text')
    
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    
    # 检查用户已有剪贴板数量
    clip_count = ClipboardItem.query.filter_by(user_id=session['user_id']).count()
    
    # 如果超过20条，删除最旧的记录
    if clip_count >= 20:
        oldest_clip = ClipboardItem.query.filter_by(user_id=session['user_id']).order_by(ClipboardItem.timestamp.asc()).first()
        if oldest_clip:
            db.session.delete(oldest_clip)
    
    # 添加新记录
    clip = ClipboardItem(content=content, content_type=content_type, user_id=session['user_id'])
    db.session.add(clip)
    db.session.commit()
    
    return jsonify({'message': '添加成功', 'id': clip.id}), 201

# 获取剪贴板内容
@app.route('/api/clipboard', methods=['GET'])
def get_clipboard():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    clips = ClipboardItem.query.filter_by(user_id=session['user_id']).order_by(ClipboardItem.timestamp.desc()).all()
    result = []
    
    for clip in clips:
        result.append({
            'id': clip.id,
            'content': clip.content,
            'content_type': clip.content_type,
            'timestamp': clip.timestamp.isoformat()
        })
    
    return jsonify(result), 200

# 获取最新的剪贴板内容
@app.route('/api/clipboard/latest', methods=['GET'])
def get_latest_clipboard():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    clip = ClipboardItem.query.filter_by(user_id=session['user_id']).order_by(ClipboardItem.timestamp.desc()).first()
    
    if not clip:
        return jsonify({'error': '没有剪贴板内容'}), 404
    
    return jsonify({
        'id': clip.id,
        'content': clip.content,
        'content_type': clip.content_type,
        'timestamp': clip.timestamp.isoformat()
    }), 200

# 删除剪贴板内容
@app.route('/api/clipboard/<int:clip_id>', methods=['DELETE'])
def delete_clipboard(clip_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    clip = ClipboardItem.query.filter_by(id=clip_id, user_id=session['user_id']).first()
    
    if not clip:
        return jsonify({'error': '剪贴板内容不存在或无权限删除'}), 404
    
    db.session.delete(clip)
    db.session.commit()
    
    return jsonify({'message': '删除成功'}), 200

# 获取用户的所有在线客户端
@app.route('/api/clients', methods=['GET'])
def get_clients():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    clients = ClientConnection.query.filter_by(user_id=session['user_id'], is_online=True).all()
    result = []
    
    for client in clients:
        result.append({
            'client_id': client.client_id,
            'name': client.name,
            'last_seen': client.last_seen.isoformat()
        })
    
    return jsonify(result), 200

# 发送模拟输入指令到客户端
@app.route('/api/simulate_typing', methods=['POST'])
def simulate_typing():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    data = request.get_json()
    client_id = data.get('client_id')
    content = data.get('content')
    typing_speed = data.get('typing_speed', 100)  # 默认速度为100ms
    
    if not client_id or not content:
        return jsonify({'error': '客户端ID和内容不能为空'}), 400
    
    # 检查客户端是否存在且属于当前用户
    client = ClientConnection.query.filter_by(client_id=client_id, user_id=session['user_id']).first()
    if not client:
        return jsonify({'error': '客户端不存在或不属于当前用户'}), 404
    
    # 创建一个特殊的剪贴板项用于模拟输入
    typing_command = {
        'action': 'simulate_typing',
        'content': content,
        'typing_speed': typing_speed,
        'command_id': str(uuid.uuid4())
    }
    
    # 将命令保存为剪贴板内容，但使用特殊的content_type标记
    clip = ClipboardItem(
        content=json.dumps(typing_command),
        content_type='typing_command',
        user_id=session['user_id']
    )
    db.session.add(clip)
    db.session.commit()
    
    return jsonify({
        'message': '模拟输入指令已发送',
        'command_id': typing_command['command_id']
    }), 201

# 修改客户端名称
@app.route('/api/clients/<string:client_id>', methods=['PUT'])
def update_client(client_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
        
    data = request.get_json()
    new_name = data.get('name')
    
    if not new_name:
        return jsonify({'error': '新名称不能为空'}), 400
    
    client = ClientConnection.query.filter_by(client_id=client_id, user_id=session['user_id']).first()
    if not client:
        return jsonify({'error': '客户端不存在或不属于当前用户'}), 404
    
    client.name = new_name
    db.session.commit()
    
    return jsonify({'message': '客户端名称修改成功'}), 200

# 删除客户端
@app.route('/api/clients/<string:client_id>', methods=['DELETE'])
def delete_client(client_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    client = ClientConnection.query.filter_by(client_id=client_id, user_id=session['user_id']).first()
    if not client:
        return jsonify({'error': '客户端不存在或不属于当前用户'}), 404
    
    db.session.delete(client)
    db.session.commit()
    
    return jsonify({'message': '客户端删除成功'}), 200

# 前端页面路由
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)