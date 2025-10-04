# 图片视频二维码生成器

一个基于 Flask 的图片和视频上传系统，支持生成二维码，扫描后可直接播放或查看媒体内容。

## 🚀 功能特性

- **多媒体上传**: 支持图片和视频文件上传
- **七牛云存储**: 自动上传到七牛云对象存储
- **二维码生成**: 为每个上传的文件生成唯一二维码
- **扫码播放**: 扫描二维码即可直接播放视频或查看图片
- **响应式设计**: 支持桌面端和移动端
- **拖拽上传**: 支持拖拽文件到上传区域
- **实时预览**: 上传前可预览选择的文件
- **全屏播放**: 支持视频全屏播放功能

## 📁 项目结构

```
qiniu_upload_qrcode/
├── app.py               # Flask 后端应用
├── templates/
│   ├── index.html       # 主页面（上传界面）
│   └── play.html        # 媒体播放页面
├── static/
│   ├── uploads/         # 临时上传目录
│   └── qrcodes/         # 临时二维码存储
├── requirements.txt     # Python 依赖
└── README.md           # 项目说明
```

## 🛠️ 技术栈

- **后端**: Flask 2.3.3
- **存储**: 七牛云对象存储
- **二维码**: qrcode 库
- **图片处理**: Pillow
- **前端**: HTML5 + CSS3 + JavaScript

## 📦 安装和配置

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd qiniu_upload_qrcode
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置七牛云

在 `app.py` 文件中修改七牛云配置：

```python
# 七牛云配置
QINIU_ACCESS_KEY = 'your_access_key'      # 替换为您的 Access Key
QINIU_SECRET_KEY = 'your_secret_key'      # 替换为您的 Secret Key
QINIU_BUCKET_NAME = 'your_bucket_name'    # 替换为您的存储空间名称
QINIU_DOMAIN = 'your_domain'              # 替换为您的七牛云域名
```

### 4. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动。

## 🎯 使用方法

### 上传文件

1. 访问 `http://localhost:5000`
2. 点击上传区域选择文件，或直接拖拽文件到上传区域
3. 支持的文件格式：
   - **图片**: PNG, JPG, JPEG, GIF
   - **视频**: MP4, AVI, MOV, WMV, FLV, WEBM, MKV
4. 点击"上传并生成二维码"按钮
5. 等待上传完成，系统会显示生成的二维码

### 扫码播放

1. 使用手机扫描生成的二维码
2. 自动跳转到播放页面
3. 视频文件会自动开始播放
4. 图片文件会直接显示

## 🔧 API 接口

### 上传文件

```
POST /api/upload
Content-Type: multipart/form-data

参数:
- file: 上传的文件

返回:
{
  "success": true,
  "file_id": "uuid",
  "media_url": "七牛云文件URL",
  "qrcode_url": "二维码图片URL",
  "play_url": "播放页面URL",
  "is_video": true/false,
  "filename": "原始文件名",
  "message": "成功消息"
}
```

### 获取媒体信息

```
GET /api/media/<file_id>

返回:
{
  "file_id": "文件ID",
  "media_url": "媒体文件URL",
  "exists": true/false
}
```

### 下载二维码

```
GET /download/<file_id>

返回: 二维码图片文件
```

## 📱 播放页面功能

- **自动播放**: 视频文件打开后自动开始播放
- **全屏播放**: 支持全屏模式观看
- **文件下载**: 可以下载原始媒体文件
- **响应式设计**: 适配各种屏幕尺寸
- **错误处理**: 文件不存在时显示友好错误信息

## ⚙️ 配置说明

### 文件大小限制

默认最大文件大小为 500MB，可在 `app.py` 中修改：

```python
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
```

### 支持的文件格式

可在 `app.py` 中的 `ALLOWED_EXTENSIONS` 变量中修改支持的文件格式：

```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
```

## 🔒 安全注意事项

1. **文件类型验证**: 系统会验证上传文件的类型
2. **文件大小限制**: 防止过大的文件上传
3. **唯一文件名**: 使用 UUID 生成唯一文件名，避免冲突
4. **临时文件清理**: 上传完成后自动清理本地临时文件

## 🚀 部署建议

### 生产环境部署

1. **使用 Gunicorn**:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. **使用 Nginx 反向代理**:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **HTTPS 配置**: 建议在生产环境使用 HTTPS

### Docker 部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

构建和运行：

```bash
docker build -t qrcode-generator .
docker run -p 5000:5000 qrcode-generator
```

## 🐛 常见问题

### Q: 上传失败怎么办？

A: 检查七牛云配置是否正确，网络连接是否正常，文件大小是否超出限制。

### Q: 二维码扫描后无法播放？

A: 确保七牛云域名配置正确，文件已成功上传到七牛云。

### Q: 如何修改上传文件大小限制？

A: 在 `app.py` 中修改 `MAX_CONTENT_LENGTH` 配置。

### Q: 支持哪些视频格式？

A: 目前支持 MP4, AVI, MOV, WMV, FLV, WEBM, MKV 格式。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请通过以下方式联系：

- 提交 Issue
- 发送邮件至 [your-email@example.com]

---

**注意**: 使用前请确保已正确配置七牛云存储服务，并替换所有示例中的配置信息。
