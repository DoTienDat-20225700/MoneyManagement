"""
Script thực thi seed dữ liệu demo cho môi trường kiểm thử E2E.
Chạy `seed_demo --reset --yes` với hubSettings.settings_e2e.
Bảo toàn tính fail-fast nghiêm ngặt 100%: Mọi lỗi vi phạm trong verify_demo_data() đều fail ngay lập tức (exit code 1).
"""
import os
import sys

# Đảm bảo thư mục backend nằm trong PYTHONPATH
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hubSettings.settings_e2e')
django.setup()

from django.core.management import call_command, CommandError

try:
    call_command('seed_demo', '--reset', '--yes')
    print("✓ seed_demo hoàn tất 100% không có bất kỳ lỗi vi phạm nào.")
    sys.exit(0)
except CommandError as err:
    print(f"❌ Lỗi nghiêm trọng: seed_demo thất bại: {err}", file=sys.stderr)
    raise err
