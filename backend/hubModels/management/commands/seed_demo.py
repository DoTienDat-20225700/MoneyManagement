import os
import sys
from datetime import date
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django.utils import timezone

from hubModels.demo_seed import (
    DEMO_ACCOUNTS,
    DEMO_USER_SAFE_EMAIL,
    DEMO_USER_STRESSED_EMAIL,
    DemoDataSeeder,
    delete_demo_user_data,
    get_demo_password,
    is_demo_seeded,
    verify_demo_data,
)
from hubModels.models import HubUser
from hubModels.services.forecasting import CashFlowForecastService


class Command(BaseCommand):
    help = (
        "Tạo bộ dữ liệu demo chuẩn hoá cho MoneyManagement, thể hiện F05 (cảnh báo ngân sách), "
        "F02 (sổ nợ & trả góp) và F03 (dự báo dòng tiền) cùng các tính năng truyền thống."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Xoá dữ liệu của 2 tài khoản demo và tạo lại từ đầu.',
        )
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Bỏ qua bước xác nhận khi chạy với --reset.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Cho phép chạy command ngay cả khi settings.DEBUG là False.',
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=2026,
            help='Random seed để sinh dữ liệu tái lập (mặc định 2026).',
        )
        parser.add_argument(
            '--write-guide',
            type=str,
            default=None,
            help='Đường dẫn file markdown để xuất tài liệu kịch bản demo từng bước.',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)
        yes = options.get('yes', False)
        force = options.get('force', False)
        seed = options.get('seed', 2026)
        guide_path = options.get('write_guide')

        # Safety Check: DEBUG protection
        if not settings.DEBUG and not force:
            raise CommandError(
                "LỖI AN TOÀN: Command seed_demo chỉ được phép chạy khi settings.DEBUG = True. "
                "Nếu bạn chắc chắn muốn chạy trên môi trường khác, hãy truyền cờ --force."
            )

        # Idempotency check: if demo accounts already exist and no --reset
        if not reset:
            if is_demo_seeded():
                self.stdout.write(
                    self.style.WARNING("Dữ liệu demo đã có, dùng --reset để tạo lại")
                )
                return

        # Confirmation if --reset
        if reset and not yes:
            confirm = input(
                "Bạn có chắc chắn muốn xoá và tạo lại dữ liệu cho 2 tài khoản demo "
                f"({', '.join(DEMO_ACCOUNTS.keys())})? [y/N]: "
            )
            if confirm.lower() not in ('y', 'yes'):
                self.stdout.write("Huỷ thao tác theo yêu cầu người dùng.")
                return

        self.stdout.write(self.style.MIGRATE_HEADING("=== BẮT ĐẦU SINH DỮ LIỆU DEMO ==="))
        today = timezone.localdate()

        # F05 rule 50% warning
        import calendar
        days_in_curr_month = calendar.monthrange(today.year, today.month)[1]
        if today.day <= days_in_curr_month / 2:
            self.stdout.write(
                self.style.WARNING(
                    "CẢNH BÁO F05: Gợi ý tái cân bằng sẽ trống vì chưa qua nửa tháng; "
                    "hãy chạy lại sau ngày 16 hoặc dùng cho demo ở nửa sau của tháng."
                )
            )

        # Seeding inside atomic transaction
        seeder = DemoDataSeeder(seed=seed, as_of_date=today)
        with db_transaction.atomic():
            user1, user2 = seeder.seed_all()

        self.stdout.write(self.style.SUCCESS("✓ Đã sinh thành công dữ liệu cho 2 tài khoản demo."))

        # Verify both accounts
        violations1 = verify_demo_data(user1, as_of_date=today)
        violations2 = verify_demo_data(user2, as_of_date=today)

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(self.style.MIGRATE_HEADING("KIỂM CHỨNG TÍNH NHẤT QUÁN:"))
        if not violations1:
            self.stdout.write(f"  • {user1.email}: " + self.style.SUCCESS("KIỂM CHỨNG: OK"))
        else:
            self.stdout.write(f"  • {user1.email}: " + self.style.ERROR(f"VI PHẠM ({len(violations1)} lỗi):"))
            for v in violations1:
                self.stdout.write(f"      - {v}")

        if not violations2:
            self.stdout.write(f"  • {user2.email}: " + self.style.SUCCESS("KIỂM CHỨNG: OK"))
        else:
            self.stdout.write(f"  • {user2.email}: " + self.style.ERROR(f"VI PHẠM ({len(violations2)} lỗi):"))
            for v in violations2:
                self.stdout.write(f"      - {v}")

        self.stdout.write("=" * 65)

        # Print detailed summary tables
        self._print_user_summary(user1, "KỊCH BẢN 1: CĂNG THẲNG DÒNG TIỀN (STRESSED SCENARIO)", today)
        self._print_user_summary(user2, "KỊCH BẢN 2: AN TOÀN TÀI CHÍNH (SAFE SCENARIO)", today)

        # Optionally write demo markdown guide
        if guide_path:
            self._write_demo_guide(guide_path, user1, user2, today)
            self.stdout.write(self.style.SUCCESS(f"\n✓ Đã xuất kịch bản demo chi tiết tại: {guide_path}"))

        self.stdout.write(self.style.SUCCESS("\nHoàn tất seed_demo! Sẵn sàng phục vụ demo/bảo vệ đồ án."))

    def _print_user_summary(self, user: HubUser, title: str, today: date):
        wallet = user.get_wallet()
        wallet.refresh_from_db()
        tx_count = wallet.transactions.count()
        pwd = get_demo_password()

        self.stdout.write(f"\n--- {title} ---")
        self.stdout.write(f"• Người dùng: {user.get_full_name()} | Email: {user.email}")
        self.stdout.write(f"• Mật khẩu: {pwd}")
        self.stdout.write(f"• Số dư ví hiện tại: {wallet.current_amount:,.2f} đ | Tổng giao dịch: {tx_count}")

        # Budgets table
        self.stdout.write("\n  [Ngân sách tháng hiện tại]")
        budgets = wallet.category_budgets.filter(month=today.month, year=today.year)
        for b in budgets:
            spent = b.get_spent()
            pct = (spent / b.amount * 100) if b.amount > 0 else 0
            status_text = "VƯỢT" if spent > b.amount else ("TIỆM CẬN" if pct >= 80 else "AN TOÀN")
            self.stdout.write(
                f"    - {b.label.name:<18}: {spent:>11,.0f} / {b.amount:>11,.0f} đ ({pct:>5.1f}%) -> {status_text}"
            )

        # Debts table
        self.stdout.write("\n  [Sổ nợ & Trả góp (F02)]")
        debts = wallet.debts.all()
        for d in debts:
            rem = d.get_remaining_amount()
            st = d.get_computed_status()
            due_str = d.due_date.strftime("%d/%m/%Y") if d.due_date else "N/A"
            self.stdout.write(
                f"    - {d.person_name:<26} [{d.type:<13}] Dư nợ: {rem:>10,.0f} đ | Hạn: {due_str:<10} | TT: {st}"
            )

        # Forecast summary (F03)
        fc = CashFlowForecastService.forecast(
            wallet=wallet,
            days=30,
            safety_buffer=Decimal("1000000.00"),
        )
        min_p = min(fc.daily_timeline, key=lambda p: Decimal(str(p['balance'])))
        min_bal = Decimal(str(min_p['balance']))
        min_offset = (min_p['date'] - today).days

        self.stdout.write("\n  [Dự báo dòng tiền 30 ngày (F03)]")
        self.stdout.write(f"    • Mức rủi ro       : {fc.risk_level}")
        self.stdout.write(f"    • Điểm chạm đáy    : Ngày {min_p['date'].strftime('%d/%m/%Y')} (+{min_offset} ngày)")
        self.stdout.write(f"    • Số dư thấp nhất  : {min_bal:,.2f} đ")
        self.stdout.write(f"    • Thiếu hụt tối đa : {fc.max_shortfall:,.2f} đ")
        self.stdout.write(f"    • Độ tin cậy       : {'Thấp (Low)' if fc.low_confidence else 'Cao (Tin cậy)'}")

        # Demo navigation tips
        self.stdout.write("\n  [Điểm nhấn thao tác khi demo/bảo vệ]")
        if user.email == DEMO_USER_STRESSED_EMAIL:
            self.stdout.write("    1. Trang /budgets: Xem 'Mua sắm' đã vượt và ấn 'Tái cân bằng' (nguồn: Giải trí / Sách vở).")
            self.stdout.write("    2. Modal thêm giao dịch: Nhập thử +500.000đ vào 'Ăn uống' -> xem cảnh báo thời gian thực.")
            self.stdout.write("    3. Trang /debts: Xem danh sách nợ phân loại theo Quá hạn (Hà) và Sắp đến hạn (Anh Hùng).")
            self.stdout.write("    4. Trang /reports -> Tab 'Dự báo': Xem biểu đồ chạm đáy âm ở ngày +25 và hồi phục sau lương.")
        else:
            self.stdout.write("    1. Đăng nhập để đối chiếu trường hợp dòng tiền an toàn (SAFE), số dư dồi dào.")
            self.stdout.write("    2. Trang /reports -> Tab 'Dự báo': Biểu đồ luôn duy trì trên ngưỡng an toàn.")

    def _write_demo_guide(self, path: str, user1: HubUser, user2: HubUser, today: date):
        pwd = get_demo_password()
        w1 = user1.get_wallet()
        fc1 = CashFlowForecastService.forecast(w1, 30, Decimal('1000000.00'))
        min_p1 = min(fc1.daily_timeline, key=lambda p: Decimal(str(p['balance'])))
        min_bal1 = Decimal(str(min_p1['balance']))
        min_day1 = (min_p1['date'] - today).days

        content = f"""# KỊCH BẢN DEMO TỪNG BƯỚC (MONEYMANAGEMENT)

**Ngày chạy dữ liệu:** {today.strftime('%d/%m/%Y')}  
**Mật khẩu dùng chung:** `{pwd}`

---

## 1. TÀI KHOẢN CHÍNH (KỊCH BẢN CĂNG THẲNG): `{user1.email}`
- **Người dùng:** {user1.get_full_name()} (Sinh viên năm cuối đi làm thêm)
- **Số dư ví ban đầu:** `{w1.current_amount:,.0f} đ`

### Bước 1: Tổng quan và Lịch sử Giao dịch
- **Mở trang:** `/` (Home) hoặc `/transactions`
- **Thao tác:** Lướt danh sách giao dịch 180 ngày qua, lọc theo loại hoặc danh mục.
- **Kỳ vọng:** Dữ liệu phong phú, biến động chân thực, có các giao dịch định kỳ (Lương, Tiền nhà, Internet).

### Bước 2: Cảnh báo & Tái cân bằng Ngân sách (F05)
- **Mở trang:** `/budgets`
- **Quan sát:**
  - Danh mục **Mua sắm**: Đã chi `1.250.000 đ / 1.000.000 đ` (VƯỢT NGÂN SÁCH). Nút **"Tái cân bằng"** xuất hiện nổi bật.
  - Danh mục **Ăn uống**: Đã chi `2.750.000 đ / 3.000.000 đ` (~91.7%, TIỆM CẬN NGƯỠNG).
  - Danh mục **Giải trí** & **Sách vở**: Đã chi dưới 40%, còn dư hạn mức.
- **Thao tác 1 (Tái cân bằng):**
  - Bấm nút "Tái cân bằng" trên thẻ Mua sắm.
  - Chọn chuyển 250.000 đ từ Giải trí sang Mua sắm.
  - Xác nhận: Ngân sách Mua sắm tăng lên, Giải trí giảm tương ứng, tổng không đổi.
- **Thao tác 2 (Kiểm tra tác động thời gian thực):**
  - Mở modal thêm giao dịch chi tiêu mới.
  - Chọn danh mục "Ăn uống", nhập số tiền `500.000 đ`.
  - **Kỳ vọng:** Hệ thống hiện thông báo cảnh báo tức thì (vượt ngân sách 250.000 đ).

### Bước 3: Quản lý Sổ nợ & Trả góp (F02)
- **Mở trang:** `/debts`
- **Quan sát Summary:**
  - Khoản quá hạn: **1 khoản** (Hà - 1.500.000 đ quá hạn 5 ngày).
  - Khoản sắp đến hạn trong 7 ngày: **1 khoản** (Anh Hùng - 2.000.000 đ đến hạn sau 6 ngày).
  - Khoản đã trả xong: **Chị Linh** (1.000.000 đ).
  - Các hợp đồng trả góp: **Laptop ASUS** (đã trả 4/12 kỳ) và **iPhone 15** (đã trả 2/6 kỳ).
- **Thao tác:** Bấm xem lịch trả góp chi tiết của Laptop để thấy kỳ tiếp theo đến hạn ngày +20.

### Bước 4: Dự báo Dòng tiền & Cảnh báo Cạn quỹ (F03)
- **Mở trang:** `/reports` -> Chuyển sang Tab **"Dự báo"** (hoặc `/forecast`)
- **Cấu hình:** Khoảng thời gian: **30 ngày**, Ngưỡng an toàn: **1.000.000 đ**.
- **Kỳ vọng:**
  - Mức cảnh báo: **CRITICAL (Báo động đỏ)**.
  - Đáy số dư: Âm `{min_bal1:,.0f} đ` tại ngày **{min_p1['date'].strftime('%d/%m/%Y')}** (ngày thứ +{min_day1}).
  - Trạng thái WARNING xuất hiện từ ngày thứ +20 trước khi chạm đáy.
  - Đường dự báo bật tăng mạnh mẽ sau ngày +27 khi nhận lương định kỳ.

---

## 2. TÀI KHOẢN ĐỐI CHỨNG (KỊCH BẢN AN TOÀN): `{user2.email}`
- **Người dùng:** {user2.get_full_name()} (Kỹ sư phần mềm thu nhập ổn định)
- **Mở trang:** Đăng xuất và đăng nhập bằng tài khoản `{user2.email}`.
- **Vào `/reports` -> Tab "Dự báo":**
  - Mức cảnh báo: **SAFE (An toàn)**.
  - Toàn bộ đường dự báo nằm vững vàng trên ngưỡng an toàn, thể hiện năng lực đối chiếu đa kịch bản của giải pháp.
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
