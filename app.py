# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify, send_file, url_for
import qrcode
import os
import uuid
import logging
from qiniu import Auth, put_file, BucketManager
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
QRCODE_FOLDER = os.getenv('QRCODE_FOLDER', 'static/qrcodes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif',
                      'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QRCODE_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = int(
    os.getenv('MAX_CONTENT_LENGTH', str(100 * 1024 * 1024)))

# 七牛云配置
QINIU_ACCESS_KEY = os.getenv('QINIU_ACCESS_KEY')
QINIU_SECRET_KEY = os.getenv('QINIU_SECRET_KEY')
QINIU_BUCKET_NAME = os.getenv('QINIU_BUCKET_NAME')
QINIU_DOMAIN = os.getenv('QINIU_DOMAIN')
QINIU_TOKEN_EXPIRE_TIME = int(os.getenv('QINIU_TOKEN_EXPIRE_TIME', '3600'))
QINIU_PRIVATE_URL_EXPIRE_TIME = int(
    os.getenv('QINIU_PRIVATE_URL_EXPIRE_TIME', '3600'))

# 初始化七牛云认证
q = Auth(QINIU_ACCESS_KEY, QINIU_SECRET_KEY)
bucket_manager = BucketManager(q)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def is_video_file(filename):
    video_extensions = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in video_extensions


def upload_to_qiniu(local_file_path, remote_filename):
    """上传文件到七牛云"""
    logger.info(f"开始上传文件到七牛云: {remote_filename}")
    logger.info(f"本地文件路径: {local_file_path}")
    logger.info(f"七牛云配置 - Bucket: {QINIU_BUCKET_NAME}, Domain: {QINIU_DOMAIN}")

    token = q.upload_token(
        QINIU_BUCKET_NAME, remote_filename, QINIU_TOKEN_EXPIRE_TIME)
    logger.info(f"生成上传token成功，过期时间: {QINIU_TOKEN_EXPIRE_TIME}秒")

    ret, info = put_file(token, remote_filename, local_file_path)
    logger.info(f"七牛云上传响应: {info}")
    logger.info(f"上传结果: {ret}")

    if info.status_code == 200:
        # 生成访问URL（基础URL，不包含签名）
        file_url = f'http://{QINIU_DOMAIN}/{remote_filename}'
        logger.info(f"上传成功，文件基础URL: {file_url}")
        return True, file_url
    else:
        logger.error(f"上传失败，状态码: {info.status_code}, 错误信息: {str(info)}")
        return False, str(info)


def generate_private_url(base_url, expire_time=None):
    """为私有bucket生成签名URL"""
    if expire_time is None:
        expire_time = QINIU_PRIVATE_URL_EXPIRE_TIME
    logger.info(f"生成私有URL: {base_url}, 过期时间: {expire_time}秒")
    private_url = q.private_download_url(base_url, expires=expire_time)
    logger.info(f"生成的私有URL: {private_url}")
    return private_url


def check_file_exists(bucket_name, key):
    """检查七牛云中文件是否存在"""
    try:
        ret, info = bucket_manager.stat(bucket_name, key)
        if info.status_code == 200:
            return True, ret
        else:
            return False, None
    except Exception as e:
        logger.error(f"检查文件存在性失败: {e}")
        return False, None


def find_file_by_id(file_id):
    """根据文件ID查找文件，尝试不同的扩展名"""
    # 可能的文件扩展名
    possible_extensions = list(ALLOWED_EXTENSIONS)

    # 首先检查二维码文件是否存在
    qrcode_filename = f"qrcodes/{file_id}_qrcode.png"
    qrcode_exists, _ = check_file_exists(QINIU_BUCKET_NAME, qrcode_filename)

    if not qrcode_exists:
        logger.info(f"二维码文件不存在: {qrcode_filename}")
        return None

    logger.info(f"二维码文件存在: {qrcode_filename}")

    # 二维码存在，现在查找对应的媒体文件
    for ext in possible_extensions:
        media_filename = f"media/{file_id}.{ext}"
        media_exists, media_info = check_file_exists(
            QINIU_BUCKET_NAME, media_filename)

        if media_exists:
            logger.info(f"找到媒体文件: {media_filename}")
            media_url = f"http://{QINIU_DOMAIN}/{media_filename}"
            qrcode_url = f"http://{QINIU_DOMAIN}/{qrcode_filename}"

            return {
                'filename': f"file.{ext}",
                'file_extension': ext,
                'media_url': media_url,
                'qrcode_url': qrcode_url,
                'is_video': ext in {'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'}
            }

    logger.warning(f"未找到文件ID {file_id} 对应的媒体文件")
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/play/<file_id>')
def play_media(file_id):
    """媒体播放页面"""
    return render_template('play.html', file_id=file_id)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件并生成二维码"""
    logger.info("收到文件上传请求")

    if 'file' not in request.files:
        logger.error("请求中没有文件")
        return jsonify({'error': '没有选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        logger.error("文件名为空")
        return jsonify({'error': '没有选择文件'}), 400

    if not allowed_file(file.filename):
        logger.error(f"不支持的文件类型: {file.filename}")
        return jsonify({'error': '不支持的文件类型'}), 400

    try:
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        filename = f"{file_id}.{file_extension}"

        logger.info(
            f"文件信息 - 原始文件名: {original_filename}, 扩展名: {file_extension}")
        logger.info(f"生成的文件ID: {file_id}, 文件名: {filename}")

        # 保存文件到本地
        local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(local_file_path)
        logger.info(f"文件已保存到本地: {local_file_path}")

        # 上传到七牛云
        remote_filename = f"media/{filename}"
        success, result = upload_to_qiniu(local_file_path, remote_filename)

        if not success:
            # 删除本地文件
            os.remove(local_file_path)
            logger.error(f"上传到七牛云失败: {result}")
            return jsonify({'error': f'上传到七牛云失败: {result}'}), 500

        # 生成播放页面的URL
        play_url = url_for('play_media', file_id=file_id, _external=True)
        logger.info(f"生成播放页面URL: {play_url}")

        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(play_url)
        qr.make(fit=True)

        # 创建二维码图片
        qr_img = qr.make_image(fill_color="black", back_color="white")

        # 保存二维码到本地
        qrcode_filename = f"{file_id}_qrcode.png"
        qrcode_local_path = os.path.join(QRCODE_FOLDER, qrcode_filename)
        qr_img.save(qrcode_local_path)
        logger.info(f"二维码已保存到本地: {qrcode_local_path}")

        # 上传二维码到七牛云
        qrcode_remote_filename = f"qrcodes/{qrcode_filename}"
        qr_success, qr_result = upload_to_qiniu(
            qrcode_local_path, qrcode_remote_filename)

        if not qr_success:
            logger.error(f"二维码上传失败: {qr_result}")
            return jsonify({'error': f'二维码上传失败: {qr_result}'}), 500

        # 清理本地文件
        os.remove(local_file_path)
        os.remove(qrcode_local_path)
        logger.info("本地临时文件已清理")

        # 生成签名URL供前端直接使用
        private_qrcode_url = generate_private_url(qr_result)

        response_data = {
            'success': True,
            'file_id': file_id,
            'media_url': result,  # 返回基础URL
            'qrcode_url': private_qrcode_url,  # 返回签名URL
            'play_url': play_url,
            'is_video': is_video_file(original_filename),
            'filename': original_filename,
            'file_extension': file_extension,
            'message': '文件上传成功，二维码已生成'
        }
        logger.info(f"上传成功，返回数据: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        # 清理可能的临时文件
        if 'local_file_path' in locals() and os.path.exists(local_file_path):
            os.remove(local_file_path)
        if 'qrcode_local_path' in locals() and os.path.exists(qrcode_local_path):
            os.remove(qrcode_local_path)

        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@app.route('/api/media/<file_id>')
def get_media_info(file_id):
    """获取媒体文件信息"""
    logger.info(f"收到获取媒体信息请求，文件ID: {file_id}")

    try:
        # 直接根据文件ID查找文件
        file_info = find_file_by_id(file_id)

        if file_info:
            logger.info(f"找到文件信息: {file_info}")

            # 生成私有bucket的签名URL
            private_media_url = generate_private_url(file_info['media_url'])
            private_qrcode_url = generate_private_url(file_info['qrcode_url'])

            response_data = {
                'file_id': file_id,
                'media_url': private_media_url,  # 返回签名URL
                'qrcode_url': private_qrcode_url,  # 返回签名URL
                'filename': file_info['filename'],
                'file_extension': file_info['file_extension'],
                'is_video': file_info['is_video'],
                'exists': True
            }
            logger.info(f"返回媒体信息: {response_data}")
            return jsonify(response_data)
        else:
            # 如果找不到文件，返回错误
            logger.warning(f"文件ID {file_id} 不存在")
            return jsonify({
                'file_id': file_id,
                'exists': False,
                'error': '文件不存在'
            }), 404
    except Exception as e:
        logger.error(f"获取媒体信息错误: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/download/<file_id>')
def download_qrcode(file_id):
    """下载二维码"""
    try:
        qrcode_path = os.path.join(QRCODE_FOLDER, f"{file_id}_qrcode.png")
        if os.path.exists(qrcode_path):
            return send_file(
                qrcode_path, as_attachment=True,
                download_name=f"{file_id}_qrcode.png")
        else:
            return jsonify({'error': '二维码文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    app.run(debug=debug, host=host, port=port)
