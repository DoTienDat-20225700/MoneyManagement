import logging
import os
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from hubModels.models import (
    CategoryBudget,
    CustomLabel,
    DebtLoan,
    DebtPayment,
    HubUser,
    SavingPlan,
    SavingPlanContribution,
    Transaction,
    TransactionRecurrency,
    Wallet,
)
from hubModels.recurring import process_due_recurring_transactions
from hubModels.services.forecasting import CashFlowForecastService

logger = logging.getLogger(__name__)

DEMO_USER_STRESSED_EMAIL = "demo@moneymanagement.local"
DEMO_USER_SAFE_EMAIL = "demo.safe@moneymanagement.local"
DEFAULT_DEMO_PASSWORD = "Demo@12345"

DEMO_ACCOUNTS = {
    DEMO_USER_STRESSED_EMAIL: {
        "first_name": "Minh Anh",
        "last_name": "Nguyễn",
        "role": "stressed",
        "desc": "Sinh viên năm cuối đi làm thêm, kịch bản căng thẳng dòng tiền",
    },
    DEMO_USER_SAFE_EMAIL: {
        "first_name": "Quốc Bảo",
        "last_name": "Trần",
        "role": "safe",
        "desc": "Người đi làm thu nhập ổn định, kịch bản an toàn tài chính",
    },
}

CATEGORIES_SETUP = [
    ("Ăn uống", "#EF4444"),
    ("Đi lại", "#F59E0B"),
    ("Nhà ở", "#3B82F6"),
    ("Giải trí", "#EC4899"),
    ("Mua sắm", "#8B5CF6"),
    ("Sách vở", "#06B6D4"),
    ("Hóa đơn & Thuê bao", "#6366F1"),
    ("Lương", "#10B981"),
    ("Thu nhập khác", "#14B8A6"),
]


def get_demo_password() -> str:
    return os.environ.get("DEMO_PASSWORD") or DEFAULT_DEMO_PASSWORD


def delete_demo_user_data(email: str) -> None:
    """Safely wipe demo user and all related data cascade-style."""
    if email not in DEMO_ACCOUNTS:
        raise ValueError(f"Cannot delete non-demo account: {email}")
    try:
        user = HubUser.objects.get(email=email)
        user.delete()
    except HubUser.DoesNotExist:
        pass


def is_demo_seeded() -> bool:
    return HubUser.objects.filter(email__in=DEMO_ACCOUNTS.keys()).count() == len(DEMO_ACCOUNTS)


def calculate_expected_wallet_balance(wallet: Wallet) -> Decimal:
    """
    Formally recalculate the expected balance of a wallet from first principles:
    expected_balance = sum(tx.wallet_effect()) + sum(debt_effect)
    Where:
      - tx.wallet_effect() = +value for EARNING, -value for EXPENSE (only if update_wallet=True)
      - debt initial contract effect:
          LOAN_GIVEN with wallet_applied=True: -principal_amount
          DEBT_BORROWED with wallet_applied=True: +principal_amount
          INSTALLMENT: 0
      - debt payment effect:
          LOAN_GIVEN payment with update_wallet=True: +amount
          DEBT_BORROWED / INSTALLMENT payment with update_wallet=True: -amount
    """
    expected = Decimal('0.00')

    # 1. Transactions
    for tx in wallet.transactions.all():
        expected += tx.wallet_effect()

    # 2. Debts initial contracts
    for debt in wallet.debts.all():
        if debt.wallet_applied:
            if debt.type == 'LOAN_GIVEN':
                expected -= debt.principal_amount
            elif debt.type == 'DEBT_BORROWED':
                expected += debt.principal_amount

        # 3. Debt payments
        for pay in debt.payments.all():
            if pay.update_wallet:
                if debt.type == 'LOAN_GIVEN':
                    expected += pay.amount
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    expected -= pay.amount

    return expected


def verify_demo_data(user: HubUser, as_of_date: Optional[date] = None) -> List[str]:
    """
    Comprehensive consistency verification for a demo account.
    Returns a list of violation messages (empty list if all criteria pass).
    """
    violations: List[str] = []
    if as_of_date is None:
        as_of_date = timezone.localdate()

    wallet = user.get_wallet()
    if not wallet:
        return [f"User {user.email} does not have a wallet."]

    # 1. Wallet balance integrity
    expected_balance = calculate_expected_wallet_balance(wallet)
    wallet.refresh_from_db()
    if wallet.current_amount != expected_balance:
        violations.append(
            f"Số dư ví ({wallet.current_amount}) không khớp với số dư tính lại từ giao dịch & nợ ({expected_balance})."
        )

    # 2. Recurring transactions consistency (no duplicate occurrences)
    recurring_txs = wallet.transactions.filter(base_transaction__isnull=False)
    seen_base_dates = set()
    for tx in recurring_txs:
        key = (tx.base_transaction_id, tx.date)
        if key in seen_base_dates:
            violations.append(f"Giao dịch định kỳ bị nhân bản cho base_id {tx.base_transaction_id} ngày {tx.date}.")
        seen_base_dates.add(key)

    # 3. Reports isolation: Check that debts are not polluting Transaction table
    debt_titles = set(wallet.debts.values_list('person_name', flat=True))
    polluted_tx = wallet.transactions.filter(title__in=debt_titles).exists()
    if polluted_tx:
        violations.append("Báo cáo Transactions bị lẫn dữ liệu hợp đồng nợ.")

    curr_month = as_of_date.month
    curr_year = as_of_date.year

    if user.email == DEMO_USER_STRESSED_EMAIL:
        # F05 Verifications for Account 1
        an_uong_lbl = wallet.labels.filter(name="Ăn uống").first()
        mua_sam_lbl = wallet.labels.filter(name="Mua sắm").first()
        giai_tri_lbl = wallet.labels.filter(name="Giải trí").first()
        sach_vo_lbl = wallet.labels.filter(name="Sách vở").first()
        di_lai_lbl = wallet.labels.filter(name="Đi lại").first()

        if not an_uong_lbl or not mua_sam_lbl or not giai_tri_lbl or not sach_vo_lbl or not di_lai_lbl:
            violations.append("Thiếu một số danh mục bắt buộc cho F05.")
        else:
            # Check Ăn uống
            b_an_uong = CategoryBudget.objects.filter(wallet=wallet, label=an_uong_lbl, month=curr_month, year=curr_year).first()
            if not b_an_uong:
                violations.append("Thiếu ngân sách Ăn uống tháng hiện tại.")
            else:
                spent = b_an_uong.get_spent()
                # Spent should be around 2.700.000 to 2.800.000 (around 90%)
                ratio = spent / b_an_uong.amount
                if not (Decimal('0.85') <= ratio < Decimal('1.00')):
                    violations.append(f"Ăn uống chưa ở trạng thái approaching (tỷ lệ {ratio * 100:.1f}%).")
                # Check impact with 500.000
                spent_after = spent + Decimal('500000.00')
                overspent = spent_after - b_an_uong.amount
                if not (Decimal('200000.00') <= overspent <= Decimal('300000.00')):
                    violations.append(
                        f"Ăn uống check-impact +500.000đ cho overspent_amount = {overspent}, ngoài khoảng 200k-300k."
                    )

            # Check Mua sắm (exceeded)
            b_mua_sam = CategoryBudget.objects.filter(wallet=wallet, label=mua_sam_lbl, month=curr_month, year=curr_year).first()
            if not b_mua_sam or b_mua_sam.get_spent() <= b_mua_sam.amount:
                violations.append("Mua sắm chưa vượt ngân sách để kích hoạt Tái cân bằng.")

            # Check Giải trí (< 40%) & Sách vở (< 25%)
            b_giai_tri = CategoryBudget.objects.filter(wallet=wallet, label=giai_tri_lbl, month=curr_month, year=curr_year).first()
            if not b_giai_tri or (b_giai_tri.get_spent() / b_giai_tri.amount) >= Decimal('0.40'):
                violations.append("Giải trí chưa đạt điều kiện đã chi < 40%.")

            b_sach_vo = CategoryBudget.objects.filter(wallet=wallet, label=sach_vo_lbl, month=curr_month, year=curr_year).first()
            if not b_sach_vo or (b_sach_vo.get_spent() / b_sach_vo.amount) >= Decimal('0.25'):
                violations.append("Sách vở chưa đạt điều kiện đã chi < 25%.")

            # Check Đi lại (~ 70%, normal)
            b_di_lai = CategoryBudget.objects.filter(wallet=wallet, label=di_lai_lbl, month=curr_month, year=curr_year).first()
            if not b_di_lai or not (Decimal('0.60') <= (b_di_lai.get_spent() / b_di_lai.amount) < Decimal('0.80')):
                violations.append("Đi lại chưa ở mức khoảng 70% (normal).")

        # F02 Verifications for Account 1
        debts = wallet.debts.all()
        types = set(debts.values_list('type', flat=True))
        if not {'LOAN_GIVEN', 'DEBT_BORROWED', 'INSTALLMENT'}.issubset(types):
            violations.append(f"Không có đủ 3 loại hợp đồng nợ (hiện có: {types}).")

        statuses = set()
        for d in debts:
            paid = d.get_total_paid()
            rem = d.principal_amount - paid
            if rem <= Decimal('0.00'):
                statuses.add('FULLY_PAID')
            elif d.due_date and as_of_date > d.due_date and rem > Decimal('0.00'):
                statuses.add('OVERDUE')
            elif paid > Decimal('0.00'):
                statuses.add('PARTIALLY_PAID')
            elif d.status == 'CLOSED':
                statuses.add('CLOSED')
            else:
                statuses.add('ACTIVE')

        if not {'PARTIALLY_PAID', 'FULLY_PAID', 'OVERDUE'}.issubset(statuses):
            violations.append(f"Không có đủ các trạng thái PARTIALLY_PAID, FULLY_PAID, OVERDUE (hiện có: {statuses}).")

        # Check summary metrics
        in_7_days = as_of_date + timedelta(days=7)
        overdue_cnt = 0
        due_7_cnt = 0
        for d in debts:
            rem = d.get_remaining_amount()
            if rem > Decimal('0.00') and d.due_date:
                if d.due_date < as_of_date:
                    overdue_cnt += 1
                elif as_of_date <= d.due_date <= in_7_days:
                    due_7_cnt += 1

        if overdue_cnt < 1:
            violations.append("Không có hợp đồng nào quá hạn (cần ít nhất 1: Hà).")
        if due_7_cnt < 1:
            violations.append("Không có hợp đồng nào đến hạn trong 7 ngày (cần ít nhất 1: Anh Hùng).")

        # F03 Verifications for Account 1
        forecast = CashFlowForecastService.forecast(
            wallet=wallet,
            days=30,
            safety_buffer=Decimal('1000000.00'),
        )
        if forecast.risk_level != 'CRITICAL':
            violations.append(f"Dự báo F03 không đạt CRITICAL (hiện là {forecast.risk_level}).")

        if forecast.low_confidence:
            violations.append("Dự báo F03 bị low_confidence = True (cần False).")

        min_day_offset = (forecast.lowest_balance_date - as_of_date).days
        min_balance = forecast.lowest_balance

        if not (18 <= min_day_offset <= 26):
            violations.append(f"Ngày chạm đáy dự báo là ngày thứ {min_day_offset}, ngoài khoảng 18-26.")

        if not (Decimal('-2000000.00') <= min_balance <= Decimal('-500000.00')):
            violations.append(
                f"Số dư thấp nhất ({min_balance}) không nằm trong khoảng thiếu hụt 0.5M - 2.0M."
            )

        # Check WARNING appeared at least 3 days before lowest balance day
        if forecast.first_warning_date is None:
            violations.append("Trạng thái WARNING không xuất hiện trong kỳ dự báo.")
        else:
            warning_day_offset = (forecast.first_warning_date - as_of_date).days
            if (min_day_offset - warning_day_offset) < 3:
                violations.append(
                    f"Trạng thái WARNING không xuất hiện trước ngày chạm đáy ít nhất 3 ngày "
                    f"(warning_day={warning_day_offset}, min_day={min_day_offset})."
                )

        # Check balance recovery after salary day (day 27)
        last_balance = forecast.projected_end_balance
        if last_balance <= Decimal('0.00'):
            violations.append(f"Số dư cuối kỳ 30 ngày ({last_balance}) không hồi phục sau ngày lương.")

    elif user.email == DEMO_USER_SAFE_EMAIL:
        # F03 Verifications for Account 2: SAFE
        forecast = CashFlowForecastService.forecast(
            wallet=wallet,
            days=30,
            safety_buffer=Decimal('1000000.00'),
        )
        if forecast.risk_level != 'SAFE':
            violations.append(f"Dự báo F03 cho tài khoản SAFE không đạt SAFE (hiện là {forecast.risk_level}).")

        # Check debts: no overdue
        overdue_cnt = 0
        for d in wallet.debts.all():
            if d.get_remaining_amount() > Decimal('0.00') and d.due_date and d.due_date < as_of_date:
                overdue_cnt += 1
        if overdue_cnt > 0:
            violations.append("Tài khoản SAFE không được có nợ quá hạn.")

    return violations


class DemoDataSeeder:
    """Deterministic, robust demo data generator."""

    def __init__(self, seed: int = 2026, as_of_date: Optional[date] = None):
        self.seed = seed
        self.as_of_date = as_of_date or timezone.localdate()
        self.rng = random.Random(seed)

    def seed_all(self) -> Tuple[HubUser, HubUser]:
        with db_transaction.atomic():
            user1 = self._seed_stressed_user()
            user2 = self._seed_safe_user()
            return user1, user2

    def _create_user_and_categories(self, email: str, role_info: dict) -> Tuple[HubUser, Wallet, Dict[str, CustomLabel]]:
        # Delete if exists
        HubUser.objects.filter(email=email).delete()

        password = get_demo_password()
        user = HubUser.objects.create_user(
            email=email,
            first_name=role_info['first_name'],
            last_name=role_info['last_name'],
            password=password,
        )
        wallet = user.get_wallet()
        label_map: Dict[str, CustomLabel] = {}
        for name, color in CATEGORIES_SETUP:
            lbl = CustomLabel.objects.create(wallet=wallet, name=name, color=color)
            label_map[name] = lbl

        return user, wallet, label_map

    def _seed_stressed_user(self) -> HubUser:
        """Kịch bản căng thẳng tài chính cho Nguyễn Minh Anh (demo@moneymanagement.local)."""
        today = self.as_of_date
        user_info = DEMO_ACCOUNTS[DEMO_USER_STRESSED_EMAIL]
        user, wallet, labels = self._create_user_and_categories(DEMO_USER_STRESSED_EMAIL, user_info)

        # -------------------------------------------------------------
        # 1. Opening Balance Transaction (Day -180)
        # We will calibrate opening balance to precisely hit target today balance
        # Target today balance ~ 14.200.000đ
        # Let's seed opening balance as 22.000.000đ
        # -------------------------------------------------------------
        opening_date = today - timedelta(days=180)
        # Calibrate opening balance based on day of month to maintain consistent 18-26d critical cashflow dip
        opening_amt = Decimal("24700000.00") - Decimal(str((today.day - 17) * 420000))
        tx_opening = Transaction(
            wallet=wallet,
            title="Số dư đầu kỳ",
            value=opening_amt,
            type="EARNING",
            date=opening_date,
            label=labels["Thu nhập khác"],
            update_wallet=True,
        )
        tx_opening.save(is_first_save=True)

        # -------------------------------------------------------------
        # 2. Recurring Transactions & History Generation
        # We set base dates 6 months ago (approx 180 days)
        # Recurring events:
        # - Lương: Monthly +15.000.000đ.
        #   We want next month's salary to arrive at today + 27 days!
        #   Let salary day offset from monthly cycle match:
        #   base_date = (today + timedelta(days=27)) - relativedelta(months=6)
        # -------------------------------------------------------------
        salary_base_date = (today + timedelta(days=27)) - relativedelta(months=6)
        tx_salary = Transaction(
            wallet=wallet,
            title="Lương hàng tháng (Công ty Công nghệ)",
            value=Decimal("15000000.00"),
            type="EARNING",
            date=salary_base_date,
            label=labels["Lương"],
            recurrent=True,
            update_wallet=True,
        )
        tx_salary.save(is_first_save=True)
        rec_salary = TransactionRecurrency.objects.create(
            transaction=tx_salary,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx_salary.recurrency = rec_salary
        tx_salary.save(update_fields=['recurrency'])

        # - Tiền nhà: Monthly -4.500.000đ. Next occurrence on today + 9 days!
        rent_base_date = (today + timedelta(days=9)) - relativedelta(months=6)
        tx_rent = Transaction(
            wallet=wallet,
            title="Tiền thuê nhà trọ & dịch vụ",
            value=Decimal("4500000.00"),
            type="EXPENSE",
            date=rent_base_date,
            label=labels["Nhà ở"],
            recurrent=True,
            update_wallet=True,
        )
        tx_rent.save(is_first_save=True)
        rec_rent = TransactionRecurrency.objects.create(
            transaction=tx_rent,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx_rent.recurrency = rec_rent
        tx_rent.save(update_fields=['recurrency'])

        # - Internet & Điện nước: Monthly -1.200.000đ. Next occurrence on today + 14 days!
        bill_base_date = (today + timedelta(days=14)) - relativedelta(months=6)
        tx_bill = Transaction(
            wallet=wallet,
            title="Hóa đơn điện nước & Internet cáp quang",
            value=Decimal("1200000.00"),
            type="EXPENSE",
            date=bill_base_date,
            label=labels["Hóa đơn & Thuê bao"],
            recurrent=True,
            update_wallet=True,
        )
        tx_bill.save(is_first_save=True)
        rec_bill = TransactionRecurrency.objects.create(
            transaction=tx_bill,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx_bill.recurrency = rec_bill
        tx_bill.save(update_fields=['recurrency'])

        # - Thuê bao (Netflix & Spotify & Gym): Monthly -800.000đ. Next occurrence on today + 16 days!
        sub_base_date = (today + timedelta(days=16)) - relativedelta(months=6)
        tx_sub = Transaction(
            wallet=wallet,
            title="Gói tập Gym & Thuê bao giải trí",
            value=Decimal("800000.00"),
            type="EXPENSE",
            date=sub_base_date,
            label=labels["Hóa đơn & Thuê bao"],
            recurrent=True,
            update_wallet=True,
        )
        tx_sub.save(is_first_save=True)
        rec_sub = TransactionRecurrency.objects.create(
            transaction=tx_sub,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx_sub.recurrency = rec_sub
        tx_sub.save(update_fields=['recurrency'])

        # Materialize all past recurring occurrences up to today!
        process_due_recurring_transactions(as_of_date=today)

        # -------------------------------------------------------------
        # 3. Variable Daily Expenses Over Past 180 Days
        # Split into:
        # - Past months (before curr_month): realistic burn rate ~200k/day
        # - Current month: carefully calibrated to meet exact F05 budget specs!
        # -------------------------------------------------------------
        curr_month_start = today.replace(day=1)
        day_cursor = opening_date + timedelta(days=1)

        # Historical days before current month
        while day_cursor < curr_month_start:
            is_weekend = day_cursor.weekday() in (5, 6)
            # base food expense
            food_val = Decimal(str(self.rng.randint(90, 160) * 1000))
            if is_weekend:
                food_val += Decimal("50000.00")

            tx = Transaction(
                wallet=wallet,
                title="Ăn uống hàng ngày",
                value=food_val,
                type="EXPENSE",
                date=day_cursor,
                label=labels["Ăn uống"],
                update_wallet=True,
            )
            tx.save(is_first_save=True)

            # Transport / coffee
            if self.rng.random() < 0.5:
                tx_commute = Transaction(
                    wallet=wallet,
                    title="Xăng xe & Gửi xe",
                    value=Decimal(str(self.rng.randint(30, 70) * 1000)),
                    type="EXPENSE",
                    date=day_cursor,
                    label=labels["Đi lại"],
                    update_wallet=True,
                )
                tx_commute.save(is_first_save=True)

            # Occasional shopping / entertainment / books
            r = self.rng.random()
            if r < 0.15:
                tx_ent = Transaction(
                    wallet=wallet,
                    title="Cà phê & xem phim",
                    value=Decimal(str(self.rng.randint(80, 200) * 1000)),
                    type="EXPENSE",
                    date=day_cursor,
                    label=labels["Giải trí"],
                    update_wallet=True,
                )
                tx_ent.save(is_first_save=True)
            elif r < 0.25:
                tx_shop = Transaction(
                    wallet=wallet,
                    title="Mua đồ dùng cá nhân",
                    value=Decimal(str(self.rng.randint(150, 400) * 1000)),
                    type="EXPENSE",
                    date=day_cursor,
                    label=labels["Mua sắm"],
                    update_wallet=True,
                )
                tx_shop.save(is_first_save=True)

            # Occasional outlier in history (e.g. course or repair)
            if (today - day_cursor).days in (45, 110):
                tx_outlier = Transaction(
                    wallet=wallet,
                    title="Bảo dưỡng xe máy định kỳ & thay lốp",
                    value=Decimal("1250000.00"),
                    type="EXPENSE",
                    date=day_cursor,
                    label=labels["Đi lại"],
                    update_wallet=True,
                )
                tx_outlier.save(is_first_save=True)

            day_cursor += timedelta(days=1)

        # -------------------------------------------------------------
        # Current month variable expenses (up to today):
        # We need exact totals:
        # Ăn uống: total spent = 2.750.000đ
        # Mua sắm: total spent = 1.250.000đ
        # Giải trí: total spent = 500.000đ
        # Sách vở: total spent = 150.000đ
        # Đi lại: total spent = 840.000đ
        # Spread these across days 1..today.day
        # -------------------------------------------------------------
        days_count = max(1, today.day)

        # Ăn uống: 2.750.000đ
        an_uong_slices = self._partition_amount(Decimal("2750000.00"), days_count)
        for i, val in enumerate(an_uong_slices):
            d = curr_month_start + timedelta(days=i)
            tx = Transaction(
                wallet=wallet,
                title="Bữa ăn hàng ngày",
                value=val,
                type="EXPENSE",
                date=d,
                label=labels["Ăn uống"],
                update_wallet=True,
            )
            tx.save(is_first_save=True)

        # Mua sắm: 1.250.000đ (1-2 transactions)
        d_shop1 = curr_month_start + timedelta(days=min(today.day - 1, max(0, today.day // 3)))
        tx_shop1 = Transaction(
            wallet=wallet,
            title="Quần áo & Giày thể thao",
            value=Decimal("850000.00"),
            type="EXPENSE",
            date=d_shop1,
            label=labels["Mua sắm"],
            update_wallet=True,
        )
        tx_shop1.save(is_first_save=True)

        d_shop2 = curr_month_start + timedelta(days=min(today.day - 1, max(0, 2 * today.day // 3)))
        tx_shop2 = Transaction(
            wallet=wallet,
            title="Phụ kiện công nghệ",
            value=Decimal("400000.00"),
            type="EXPENSE",
            date=d_shop2,
            label=labels["Mua sắm"],
            update_wallet=True,
        )
        tx_shop2.save(is_first_save=True)

        # Giải trí: 500.000đ
        d_ent = curr_month_start + timedelta(days=min(today.day - 1, max(0, today.day // 2)))
        tx_ent = Transaction(
            wallet=wallet,
            title="Đi xem phim & ăn lẩu cùng bạn",
            value=Decimal("500000.00"),
            type="EXPENSE",
            date=d_ent,
            label=labels["Giải trí"],
            update_wallet=True,
        )
        tx_ent.save(is_first_save=True)

        # Sách vở: 150.000đ
        d_book = curr_month_start + timedelta(days=min(today.day - 1, max(0, today.day // 4)))
        tx_book = Transaction(
            wallet=wallet,
            title="Sách lập trình Python & Algorithms",
            value=Decimal("150000.00"),
            type="EXPENSE",
            date=d_book,
            label=labels["Sách vở"],
            update_wallet=True,
        )
        tx_book.save(is_first_save=True)

        # Đi lại: 840.000đ
        di_lai_slices = self._partition_amount(Decimal("840000.00"), min(days_count, 6))
        for i, val in enumerate(di_lai_slices):
            step = max(1, days_count // len(di_lai_slices))
            d = curr_month_start + timedelta(days=min(today.day - 1, i * step))
            tx = Transaction(
                wallet=wallet,
                title="Đổ xăng xe máy Honda",
                value=val,
                type="EXPENSE",
                date=d,
                label=labels["Đi lại"],
                update_wallet=True,
            )
            tx.save(is_first_save=True)

        # -------------------------------------------------------------
        # 4. Monthly Budgets Setup (Current Month & 2 Prior Months)
        # -------------------------------------------------------------
        months_to_seed = [
            (today.month, today.year),
            ((today.replace(day=1) - timedelta(days=1)).month, (today.replace(day=1) - timedelta(days=1)).year),
            ((today.replace(day=1) - timedelta(days=32)).month, (today.replace(day=1) - timedelta(days=32)).year),
        ]

        budgets_config = [
            ("Ăn uống", Decimal("3000000.00")),
            ("Mua sắm", Decimal("1000000.00")),
            ("Giải trí", Decimal("1500000.00")),
            ("Sách vở", Decimal("800000.00")),
            ("Đi lại", Decimal("1200000.00")),
            ("Nhà ở", Decimal("5000000.00")),
            ("Hóa đơn & Thuê bao", Decimal("2200000.00")),
        ]

        for m, y in months_to_seed:
            for lbl_name, b_amt in budgets_config:
                CategoryBudget.objects.create(
                    wallet=wallet,
                    label=labels[lbl_name],
                    amount=b_amt,
                    month=m,
                    year=y,
                )

        # -------------------------------------------------------------
        # 5. Saving Plans & Contributions
        # - Laptop mới: goal 20M, reached 12M (~60%)
        # - Du lịch Đà Nẵng: goal 8M, reached 6.8M (~85%)
        # - Quỹ khẩn cấp: goal 30M, reached 7.5M (~25%)
        # -------------------------------------------------------------
        p1 = SavingPlan.objects.create(
            wallet=wallet,
            title="Đổi laptop lập trình cao cấp",
            amount=Decimal("20000000.00"),
            goal_date=today + timedelta(days=120),
            description="Tích luỹ đổi laptop cấu hình mạnh phục vụ tốt nghiệp",
            active=True,
        )
        SavingPlanContribution.objects.create(
            saving_plan=p1, user=user, amount=Decimal("4000000.00"),
            date=today - timedelta(days=90), description="Tiết kiệm tháng 1",
            idempotency_key=f"demo_p1_c1_{user.pk}"
        )
        SavingPlanContribution.objects.create(
            saving_plan=p1, user=user, amount=Decimal("4000000.00"),
            date=today - timedelta(days=60), description="Tiết kiệm tháng 2",
            idempotency_key=f"demo_p1_c2_{user.pk}"
        )
        SavingPlanContribution.objects.create(
            saving_plan=p1, user=user, amount=Decimal("4000000.00"),
            date=today - timedelta(days=30), description="Tiết kiệm tháng 3",
            idempotency_key=f"demo_p1_c3_{user.pk}"
        )

        p2 = SavingPlan.objects.create(
            wallet=wallet,
            title="Du lịch Đà Nẵng cùng nhóm bạn",
            amount=Decimal("8000000.00"),
            goal_date=today + timedelta(days=45),
            description="Chuyến đi kỷ niệm thời sinh viên",
            active=True,
        )
        SavingPlanContribution.objects.create(
            saving_plan=p2, user=user, amount=Decimal("3500000.00"),
            date=today - timedelta(days=40), description="Đặt cọc tour & vé bay",
            idempotency_key=f"demo_p2_c1_{user.pk}"
        )
        SavingPlanContribution.objects.create(
            saving_plan=p2, user=user, amount=Decimal("3300000.00"),
            date=today - timedelta(days=15), description="Tiền phòng khách sạn",
            idempotency_key=f"demo_p2_c2_{user.pk}"
        )

        p3 = SavingPlan.objects.create(
            wallet=wallet,
            title="Quỹ dự phòng khẩn cấp",
            amount=Decimal("30000000.00"),
            goal_date=today + timedelta(days=300),
            description="Khoản phòng ngừa 3 tháng chi tiêu",
            active=True,
        )
        SavingPlanContribution.objects.create(
            saving_plan=p3, user=user, amount=Decimal("7500000.00"),
            date=today - timedelta(days=50), description="Trích thưởng làm thêm",
            idempotency_key=f"demo_p3_c1_{user.pk}"
        )

        # -------------------------------------------------------------
        # 6. F02 Debt & Installment Contracts (Official creation path)
        # -------------------------------------------------------------
        # Cho vay 1: "Nam" 5.000.000đ, đã thu hồi 2.000.000đ (PARTIALLY_PAID), hạn trong 10 ngày (today + 10)
        debt_nam = DebtLoan.create_from_json({
            'person_name': 'Nam (Bạn đại học)',
            'type': 'LOAN_GIVEN',
            'principal_amount': '5000000.00',
            'start_date': (today - timedelta(days=20)).isoformat(),
            'due_date': (today + timedelta(days=10)).isoformat(),
            'description': 'Cho Nam mượn đóng học phí chứng chỉ, hẹn trả trong tháng',
            'update_wallet': True,
        }, user.pk)
        DebtPayment.create_from_json(debt_nam.pk, user, {
            'amount': '2000000.00',
            'date': (today - timedelta(days=5)).isoformat(),
            'update_wallet': True,
            'note': 'Nam chuyển trả trước đợt 1',
        })

        # Cho vay 2: "Hà" 1.500.000đ, đã quá hạn 5 ngày (due_date = today - 5), chưa thu (OVERDUE)
        DebtLoan.create_from_json({
            'person_name': 'Hà (Đồng nghiệp cũ)',
            'type': 'LOAN_GIVEN',
            'principal_amount': '1500000.00',
            'start_date': (today - timedelta(days=25)).isoformat(),
            'due_date': (today - timedelta(days=5)).isoformat(),
            'description': 'Cho Hà mượn tiền mua tài liệu',
            'update_wallet': True,
        }, user.pk)

        # Đi vay 1: "Anh Hùng" 2.000.000đ, đến hạn sau 6 ngày (today + 6), nằm trong cảnh báo 7 ngày
        DebtLoan.create_from_json({
            'person_name': 'Anh Hùng (Anh họ)',
            'type': 'DEBT_BORROWED',
            'principal_amount': '2000000.00',
            'start_date': (today - timedelta(days=10)).isoformat(),
            'due_date': (today + timedelta(days=6)).isoformat(),
            'description': 'Mượn anh Hùng xoay tiền đột xuất',
            'update_wallet': True,
        }, user.pk)

        # Đi vay 2: "Chị Linh" 1.000.000đ, đã trả xong (FULLY_PAID)
        debt_linh = DebtLoan.create_from_json({
            'person_name': 'Chị Linh',
            'type': 'DEBT_BORROWED',
            'principal_amount': '1000000.00',
            'start_date': (today - timedelta(days=40)).isoformat(),
            'due_date': (today - timedelta(days=10)).isoformat(),
            'description': 'Mượn chị Linh mua sách',
            'update_wallet': True,
        }, user.pk)
        DebtPayment.create_from_json(debt_linh.pk, user, {
            'amount': '1000000.00',
            'date': (today - timedelta(days=12)).isoformat(),
            'update_wallet': True,
            'note': 'Đã chuyển khoản trả đủ chị Linh',
        })

        # Trả góp 1: "Laptop ASUS Zenbook" 24.000.000đ / 12 tháng, đã trả 4 kỳ (mỗi kỳ 2.000.000đ)
        # Next installment falls on day today + 20!
        # Start date = (today + timedelta(days=20)) - relativedelta(months=5)
        laptop_start = (today + timedelta(days=20)) - relativedelta(months=5)
        debt_laptop = DebtLoan.create_from_json({
            'person_name': 'Thế Giới Di Động (Laptop ASUS)',
            'type': 'INSTALLMENT',
            'principal_amount': '24000000.00',
            'installment_months': 12,
            'start_date': laptop_start.isoformat(),
            'description': 'Trả góp 0% qua thẻ tín dụng',
            'update_wallet': False,
        }, user.pk)
        for k in range(1, 5):
            pay_date = laptop_start + relativedelta(months=k)
            DebtPayment.create_from_json(debt_laptop.pk, user, {
                'amount': '2000000.00',
                'date': pay_date.isoformat(),
                'update_wallet': True,
                'note': f'Thanh toán trả góp kỳ {k}/12',
            })

        # Trả góp 2: "Điện thoại iPhone 15" 15.000.000đ / 6 tháng, đã trả 2 kỳ (mỗi kỳ 2.500.000đ)
        # Next installment falls on day today + 22!
        # Start date = (today + timedelta(days=22)) - relativedelta(months=3)
        phone_start = (today + timedelta(days=22)) - relativedelta(months=3)
        debt_phone = DebtLoan.create_from_json({
            'person_name': 'FPT Shop (iPhone 15)',
            'type': 'INSTALLMENT',
            'principal_amount': '15000000.00',
            'installment_months': 6,
            'start_date': phone_start.isoformat(),
            'description': 'Trả góp máy điện thoại',
            'update_wallet': False,
        }, user.pk)
        for k in range(1, 3):
            pay_date = phone_start + relativedelta(months=k)
            DebtPayment.create_from_json(debt_phone.pk, user, {
                'amount': '2500000.00',
                'date': pay_date.isoformat(),
                'update_wallet': True,
                'note': f'Thanh toán trả góp kỳ {k}/6',
            })

        return user

    def _seed_safe_user(self) -> HubUser:
        """Kịch bản an toàn tài chính cho Trần Quốc Bảo (demo.safe@moneymanagement.local)."""
        today = self.as_of_date
        user_info = DEMO_ACCOUNTS[DEMO_USER_SAFE_EMAIL]
        user, wallet, labels = self._create_user_and_categories(DEMO_USER_SAFE_EMAIL, user_info)

        # Opening balance
        opening_date = today - timedelta(days=180)
        tx_opening = Transaction(
            wallet=wallet,
            title="Số dư đầu kỳ",
            value=Decimal("55000000.00"),
            type="EARNING",
            date=opening_date,
            label=labels["Thu nhập khác"],
            update_wallet=True,
        )
        tx_opening.save(is_first_save=True)

        # Recurring: High Salary
        salary_base_date = (today + timedelta(days=10)) - relativedelta(months=6)
        tx_salary = Transaction(
            wallet=wallet,
            title="Tiền lương tháng (Kỹ sư phần mềm Senior)",
            value=Decimal("35000000.00"),
            type="EARNING",
            date=salary_base_date,
            label=labels["Lương"],
            recurrent=True,
            update_wallet=True,
        )
        tx_salary.save(is_first_save=True)
        rec_salary = TransactionRecurrency.objects.create(
            transaction=tx_salary,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx_salary.recurrency = rec_salary
        tx_salary.save(update_fields=['recurrency'])

        # Recurring: Rent
        rent_base_date = (today + timedelta(days=5)) - relativedelta(months=6)
        tx_rent = Transaction(
            wallet=wallet,
            title="Tiền thuê căn hộ chung cư cao cấp",
            value=Decimal("8000000.00"),
            type="EXPENSE",
            date=rent_base_date,
            label=labels["Nhà ở"],
            recurrent=True,
            update_wallet=True,
        )
        tx_rent.save(is_first_save=True)
        rec_rent = TransactionRecurrency.objects.create(
            transaction=tx_rent,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx_rent.recurrency = rec_rent
        tx_rent.save(update_fields=['recurrency'])

        process_due_recurring_transactions(as_of_date=today)

        # Controlled variable expenses
        day_cursor = opening_date + timedelta(days=1)
        while day_cursor <= today:
            if self.rng.random() < 0.6:
                tx = Transaction(
                    wallet=wallet,
                    title="Chi tiêu sinh hoạt & ăn uống",
                    value=Decimal(str(self.rng.randint(150, 300) * 1000)),
                    type="EXPENSE",
                    date=day_cursor,
                    label=labels["Ăn uống"],
                    update_wallet=True,
                )
                tx.save(is_first_save=True)
            day_cursor += timedelta(days=1)

        # Budgets (Generous limit, spending around 50%)
        m, y = today.month, today.year
        CategoryBudget.objects.create(wallet=wallet, label=labels["Ăn uống"], amount=Decimal("10000000.00"), month=m, year=y)
        CategoryBudget.objects.create(wallet=wallet, label=labels["Nhà ở"], amount=Decimal("12000000.00"), month=m, year=y)
        CategoryBudget.objects.create(wallet=wallet, label=labels["Mua sắm"], amount=Decimal("8000000.00"), month=m, year=y)

        # Debt: 1 Loan Given (on time) + 1 Small Installment
        DebtLoan.create_from_json({
            'person_name': 'Đức (Bạn thân)',
            'type': 'LOAN_GIVEN',
            'principal_amount': '5000000.00',
            'start_date': (today - timedelta(days=10)).isoformat(),
            'due_date': (today + timedelta(days=25)).isoformat(),
            'description': 'Cho bạn mượn',
            'update_wallet': True,
        }, user.pk)

        debt_inst = DebtLoan.create_from_json({
            'person_name': 'Apple Store (Apple Watch)',
            'type': 'INSTALLMENT',
            'principal_amount': '9000000.00',
            'installment_months': 6,
            'start_date': (today - relativedelta(months=3)).isoformat(),
            'description': 'Trả góp đồng hồ',
            'update_wallet': False,
        }, user.pk)
        for k in range(1, 4):
            DebtPayment.create_from_json(debt_inst.pk, user, {
                'amount': '1500000.00',
                'date': (today - relativedelta(months=3 - k)).isoformat(),
                'update_wallet': True,
                'note': f'Kỳ {k}/6',
            })

        return user

    def _partition_amount(self, total: Decimal, num_parts: int) -> List[Decimal]:
        """Split a total amount into num_parts slices rounding to thousands."""
        if num_parts <= 1:
            return [total]
        weights = [self.rng.uniform(0.7, 1.3) for _ in range(num_parts)]
        sum_w = sum(weights)
        raw_parts = [(total * Decimal(str(w / sum_w))).quantize(Decimal('1000')) for w in weights[:-1]]
        last_part = total - sum(raw_parts)
        return raw_parts + [last_part]
