import os
import django
import sys

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

# 检查admin用户是否存在
if not User.objects.filter(username='admin').exists():
    # 创建超级用户
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('管理员用户已创建成功!')
else:
    print('管理员用户已存在!') 