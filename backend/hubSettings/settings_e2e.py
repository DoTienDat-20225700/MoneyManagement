"""
Cấu hình Django Settings riêng biệt cho môi trường kiểm thử End-to-End (E2E).
Kế thừa toàn bộ settings gốc từ hubSettings.settings, sử dụng database riêng db_e2e.sqlite3
hoặc moneymanagement_e2e (nếu TEST_DB=postgres).
"""
import os
from .settings import *

# Đảm bảo môi trường E2E luôn bật DEBUG để seed_demo hoạt động
DEBUG = True

# Database riêng biệt cho E2E
test_db_type = os.environ.get('TEST_DB', '').lower()
if test_db_type in ('postgres', 'postgresql'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'moneymanagement_e2e'),
            'USER': os.environ.get('DB_USER', 'test_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'test_password'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db_e2e.sqlite3',
        }
    }


