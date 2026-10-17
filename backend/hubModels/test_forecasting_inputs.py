import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from hubModels.factory import TransactionFactory
from hubModels.models import (
    DebtLoan,
    DebtPayment,
    HubUser,
    Transaction,
    TransactionRecurrency,
    Wallet,
)
from hubModels.services.forecasting_inputs import (
    FixedEvent,
    ForecastInputs,
    get_daily_variable_spending,
    get_debt_events,
    get_forecast_inputs,
    get_recurring_events,
)


class ForecastingInputsTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.wallet.update_balance(10_000_000)

        # Other user & wallet for isolation testing
        self.other_user = self.factory.create_user()
        self.other_wallet = self.other_user.get_wallet()
        self.other_wallet.update_balance(5_000_000)

    # ------------------------------------------------------------------
    # 1. get_recurring_events tests
    # ------------------------------------------------------------------

    def test_recurring_monthly_90_days(self):
        """Một giao dịch lặp hàng tháng cho đúng các ngày trong 90 ngày."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Tien nha",
            value=Decimal("5000000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        # Horizon: 2026-01-01 to 2026-04-01 (90 days)
        # Occurrences: step 1: 2026-02-01, step 2: 2026-03-01, step 3: 2026-04-01
        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 4, 1),
            today=datetime.date(2026, 1, 1),
        )

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].date, datetime.date(2026, 2, 1))
        self.assertEqual(events[0].amount, Decimal("-5000000.00"))
        self.assertEqual(events[0].source, "RECURRING")
        self.assertEqual(events[0].source_id, base_tx.id)

        self.assertEqual(events[1].date, datetime.date(2026, 3, 1))
        self.assertEqual(events[2].date, datetime.date(2026, 4, 1))

    def test_recurring_weekly(self):
        """Giao dịch lặp hàng tuần sinh đúng các ngày cách nhau 7 ngày."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Di cho tuan",
            value=Decimal("500000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="WEEKS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 1, 23),
            today=datetime.date(2026, 1, 1),
        )

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].date, datetime.date(2026, 1, 8))
        self.assertEqual(events[1].date, datetime.date(2026, 1, 15))
        self.assertEqual(events[2].date, datetime.date(2026, 1, 22))

    def test_recurring_earning_is_positive(self):
        """EARNING mang dấu dương."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Luong thang",
            value=Decimal("20000000.00"),
            date=base_date,
            type="EARNING",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 2, 15),
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].amount, Decimal("20000000.00"))
        self.assertGreater(events[0].amount, 0)

    def test_recurring_expense_is_negative(self):
        """EXPENSE mang dấu âm."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Tien internet",
            value=Decimal("300000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 2, 15),
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].amount, Decimal("-300000.00"))
        self.assertLess(events[0].amount, 0)

    def test_recurring_skips_already_generated_transaction(self):
        """Bỏ qua lần xảy ra đã được sinh thành Transaction thật."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Tien mang",
            value=Decimal("300000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        # Occurrence step 1 is 2026-02-01. Generate it as real Transaction
        Transaction.objects.create(
            wallet=self.wallet,
            base_transaction=base_tx,
            title="Tien mang",
            value=Decimal("300000.00"),
            date=datetime.date(2026, 2, 1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=False,
        )

        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 15),
            today=datetime.date(2026, 2, 1),
        )

        # 2026-02-01 was already generated, so only 2026-03-01 should be returned
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].date, datetime.date(2026, 3, 1))

    def test_recurring_ungenerated_due_today_or_past_placed_on_today(self):
        """Lần chưa sinh nhưng đến hạn hôm nay hoặc quá khứ được đặt vào hôm nay."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Dien thoai",
            value=Decimal("200000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        # Today is 2026-02-05, but 2026-02-01 occurrence has NOT been generated by cron
        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 2, 5),
            end=datetime.date(2026, 3, 15),
            today=datetime.date(2026, 2, 5),
        )

        # The ungenerated 2026-02-01 occurrence should be shifted to today (2026-02-05)
        # Plus the future 2026-03-01 occurrence
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].date, datetime.date(2026, 2, 5))
        self.assertEqual(events[0].amount, Decimal("-200000.00"))
        self.assertEqual(events[1].date, datetime.date(2026, 3, 1))

    def test_recurring_ignores_update_wallet_false(self):
        """Bỏ qua giao dịch định kỳ có update_wallet=False."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Khong cap nhat vi",
            value=Decimal("1000000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=False,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 4, 1),
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events), 0)

    def test_recurring_respects_end_date(self):
        """Tôn trọng ngày kết thúc lặp (end_date)."""
        base_date = datetime.date(2026, 1, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Khoa hoc ngan han",
            value=Decimal("1000000.00"),
            date=base_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            end_date=timezone.make_aware(datetime.datetime(2026, 2, 15, 23, 59, 59)),
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 5, 1),
            today=datetime.date(2026, 1, 1),
        )

        # Step 1: 2026-02-01 <= end_date (kept)
        # Step 2: 2026-03-01 > end_date (stopped)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].date, datetime.date(2026, 2, 1))

    # ------------------------------------------------------------------
    # 2. get_debt_events tests
    # ------------------------------------------------------------------

    def test_debt_borrowed_in_range_with_partial_payment(self):
        """DEBT_BORROWED có due_date trong khoảng sinh đúng 1 sự kiện âm bằng dư nợ (không phải gốc nếu đã trả một phần)."""
        debt = DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Anh Nam",
            type="DEBT_BORROWED",
            principal_amount=Decimal("10000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 3, 1),
            status="PARTIALLY_PAID",
        )
        # Đã trả 3.000.000đ -> dư nợ còn 7.000.000đ
        DebtPayment.objects.create(
            debt=debt,
            amount=Decimal("3000000.00"),
            date=datetime.date(2026, 1, 15),
            update_wallet=False,
        )

        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 15),
            today=datetime.date(2026, 1, 1),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].date, datetime.date(2026, 3, 1))
        self.assertEqual(events[0].amount, Decimal("-7000000.00"))
        self.assertEqual(events[0].source, "DEBT")
        self.assertEqual(events[0].source_id, debt.id)

    def test_debt_borrowed_out_of_range_no_event(self):
        """due_date ngoài khoảng thì không sinh sự kiện."""
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Chi Lan",
            type="DEBT_BORROWED",
            principal_amount=Decimal("5000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 5, 1),
            status="ACTIVE",
        )

        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 31),
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events), 0)

    def test_debt_borrowed_overdue_placed_on_today(self):
        """DEBT_BORROWED đã quá hạn thì đặt vào hôm nay."""
        debt = DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Bac Ba",
            type="DEBT_BORROWED",
            principal_amount=Decimal("4000000.00"),
            start_date=datetime.date(2025, 12, 1),
            due_date=datetime.date(2026, 1, 15),
            status="OVERDUE",
        )

        # Today is 2026-02-01 (due_date was 2026-01-15 < today)
        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 2, 1),
            end=datetime.date(2026, 3, 1),
            today=datetime.date(2026, 2, 1),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].date, datetime.date(2026, 2, 1))
        self.assertEqual(events[0].amount, Decimal("-4000000.00"))

    def test_installment_schedule_half_paid_and_rounding(self):
        """INSTALLMENT chỉ sinh các kỳ chưa trả đủ, kỳ trả một nửa sinh phần còn thiếu, kỳ cuối đúng phần dư làm tròn."""
        # 10.000.000đ / 3 kỳ: kỳ 1: 3.333.333, kỳ 2: 3.333.333, kỳ 3: 3.333.334
        start_date = datetime.date(2026, 1, 1)
        debt = DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Mua iPhone",
            type="INSTALLMENT",
            principal_amount=Decimal("10000000.00"),
            installment_months=3,
            start_date=start_date,
            status="ACTIVE",
        )
        # Trả 5.000.000đ: kỳ 1 đủ 3.333.333đ, kỳ 2 được 1.666.667đ (còn thiếu 1.666.666đ), kỳ 3 chưa trả (thiếu 3.333.334đ)
        DebtPayment.objects.create(
            debt=debt,
            amount=Decimal("5000000.00"),
            date=datetime.date(2026, 1, 15),
            update_wallet=False,
        )

        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 4, 30),
            today=datetime.date(2026, 1, 1),
        )

        self.assertEqual(len(events), 2)
        # Kỳ 2 due_date: 2026-03-01
        self.assertEqual(events[0].date, datetime.date(2026, 3, 1))
        self.assertEqual(events[0].amount, Decimal("-1666666.00"))
        self.assertEqual(events[0].source, "INSTALLMENT")

        # Kỳ 3 due_date: 2026-04-01 (gánh phần dư làm tròn)
        self.assertEqual(events[1].date, datetime.date(2026, 4, 1))
        self.assertEqual(events[1].amount, Decimal("-3333334.00"))
        self.assertEqual(events[1].source, "INSTALLMENT")

    def test_installment_overdue_period_placed_on_today(self):
        """Kỳ trả góp chưa trả đủ nhưng đã quá hạn thì đặt vào ngày hôm nay."""
        start_date = datetime.date(2025, 11, 1)
        # Kỳ 1: 2025-12-01, Kỳ 2: 2026-01-01, Kỳ 3: 2026-02-01
        debt = DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Tu lanh",
            type="INSTALLMENT",
            principal_amount=Decimal("6000000.00"),
            installment_months=3,
            start_date=start_date,
            status="OVERDUE",
        )
        # Chưa trả đồng nào. Today = 2026-01-15.
        # Kỳ 1 (2025-12-01) quá hạn -> đặt vào today.
        # Kỳ 2 (2026-01-01) quá hạn -> đặt vào today.
        # Kỳ 3 (2026-02-01) tương lai -> giữ nguyên 2026-02-01.
        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 15),
            end=datetime.date(2026, 2, 28),
            today=datetime.date(2026, 1, 15),
        )

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].date, datetime.date(2026, 1, 15))
        self.assertEqual(events[0].amount, Decimal("-2000000.00"))

        self.assertEqual(events[1].date, datetime.date(2026, 1, 15))
        self.assertEqual(events[1].amount, Decimal("-2000000.00"))

        self.assertEqual(events[2].date, datetime.date(2026, 2, 1))
        self.assertEqual(events[2].amount, Decimal("-2000000.00"))

    def test_loan_given_ignored_by_default_and_included_when_flag_true(self):
        """LOAN_GIVEN không sinh mặc định và có sinh dương khi include_receivables=True."""
        debt = DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Ban A",
            type="LOAN_GIVEN",
            principal_amount=Decimal("3000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 2, 15),
            status="ACTIVE",
        )

        # Mặc định include_receivables=False
        events_default = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 1),
            include_receivables=False,
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events_default), 0)

        # include_receivables=True
        events_with_receivables = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 1),
            include_receivables=True,
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events_with_receivables), 1)
        self.assertEqual(events_with_receivables[0].date, datetime.date(2026, 2, 15))
        self.assertEqual(events_with_receivables[0].amount, Decimal("3000000.00"))
        self.assertGreater(events_with_receivables[0].amount, 0)
        self.assertEqual(events_with_receivables[0].source, "DEBT")

    def test_loan_given_overdue_not_included(self):
        """LOAN_GIVEN quá hạn thì không tính kể cả khi include_receivables=True."""
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Ban B no cu",
            type="LOAN_GIVEN",
            principal_amount=Decimal("2000000.00"),
            start_date=datetime.date(2025, 11, 1),
            due_date=datetime.date(2025, 12, 15),
            status="OVERDUE",
        )

        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 1),
            include_receivables=True,
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events), 0)

    def test_fully_paid_debt_ignored(self):
        """Hợp đồng FULLY_PAID không sinh sự kiện."""
        debt = DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Anh Da Tra Het",
            type="DEBT_BORROWED",
            principal_amount=Decimal("5000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 2, 15),
            status="FULLY_PAID",
        )
        DebtPayment.objects.create(
            debt=debt,
            amount=Decimal("5000000.00"),
            date=datetime.date(2026, 1, 20),
            update_wallet=False,
        )

        events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 1),
            today=datetime.date(2026, 1, 1),
        )
        self.assertEqual(len(events), 0)

    # ------------------------------------------------------------------
    # 3. get_daily_variable_spending tests
    # ------------------------------------------------------------------

    def test_daily_variable_spending_returns_exact_days_and_zeros(self):
        """get_daily_variable_spending: trả đủ days phần tử; ngày trống bằng 0."""
        end_date = datetime.date(2026, 2, 28)
        # Chỉ tạo 1 giao dịch vào ngày 2026-02-28
        Transaction.objects.create(
            wallet=self.wallet,
            title="Cafe",
            value=Decimal("50000.00"),
            date=end_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=False,
        )

        history = get_daily_variable_spending(self.wallet, end=end_date, days=60)

        self.assertEqual(len(history), 60)
        self.assertEqual(history[-1][0], end_date)
        self.assertEqual(history[-1][1], Decimal("50000.00"))
        # Các ngày trước đó trống bằng Decimal('0.00')
        self.assertEqual(history[0][1], Decimal("0.00"))
        self.assertEqual(history[-2][1], Decimal("0.00"))

        # Kiểm tra sắp xếp tăng dần theo ngày
        dates = [item[0] for item in history]
        self.assertEqual(dates, sorted(dates))

    def test_daily_variable_spending_filters_correctly(self):
        """Giao dịch sinh từ lịch định kỳ, update_wallet=False, hoặc thu nhập bị loại."""
        end_date = datetime.date(2026, 2, 28)

        # 1. Chi tiêu biến đổi hợp lệ: 100.000đ
        Transaction.objects.create(
            wallet=self.wallet,
            title="Sieu thi",
            value=Decimal("100000.00"),
            date=end_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=False,
        )

        # 2. Giao dịch sinh từ lịch định kỳ -> BỊ LOẠI
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Base",
            value=Decimal("500000.00"),
            date=datetime.date(2026, 1, 1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        Transaction.objects.create(
            wallet=self.wallet,
            base_transaction=base_tx,
            title="Generated",
            value=Decimal("500000.00"),
            date=end_date,
            type="EXPENSE",
            update_wallet=True,
            recurrent=False,
        )

        # 3. Giao dịch update_wallet=False -> BỊ LOẠI
        Transaction.objects.create(
            wallet=self.wallet,
            title="No wallet update",
            value=Decimal("200000.00"),
            date=end_date,
            type="EXPENSE",
            update_wallet=False,
            recurrent=False,
        )

        # 4. Giao dịch EARNING -> BỊ LOẠI
        Transaction.objects.create(
            wallet=self.wallet,
            title="Thu nhap",
            value=Decimal("3000000.00"),
            date=end_date,
            type="EARNING",
            update_wallet=True,
            recurrent=False,
        )

        history = get_daily_variable_spending(self.wallet, end=end_date, days=3)
        self.assertEqual(len(history), 3)
        # Chỉ có 100.000đ của giao dịch hợp lệ
        self.assertEqual(history[-1][1], Decimal("100000.00"))

    # ------------------------------------------------------------------
    # 4. Ownership Isolation tests
    # ------------------------------------------------------------------

    def test_ownership_isolation(self):
        """Cô lập quyền: dữ liệu của ví khác không xuất hiện trong bất kỳ hàm nào."""
        # Tạo dữ liệu cho ví khác (other_wallet)
        other_base = Transaction.objects.create(
            wallet=self.other_wallet,
            title="Tien nha vi khac",
            value=Decimal("8000000.00"),
            date=datetime.date(2026, 1, 1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec_other = TransactionRecurrency.objects.create(
            transaction=other_base,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        other_base.recurrency = rec_other
        other_base.save(update_fields=["recurrency"])

        DebtLoan.objects.create(
            wallet=self.other_wallet,
            person_name="No cua vi khac",
            type="DEBT_BORROWED",
            principal_amount=Decimal("15000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 2, 1),
            status="ACTIVE",
        )

        Transaction.objects.create(
            wallet=self.other_wallet,
            title="Chi tieu bien doi vi khac",
            value=Decimal("999999.00"),
            date=datetime.date(2026, 2, 1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=False,
        )

        # Gọi cho self.wallet
        rec_events = get_recurring_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 1),
            today=datetime.date(2026, 1, 1),
        )
        debt_events = get_debt_events(
            self.wallet,
            start=datetime.date(2026, 1, 1),
            end=datetime.date(2026, 3, 1),
            today=datetime.date(2026, 1, 1),
        )
        history = get_daily_variable_spending(self.wallet, end=datetime.date(2026, 2, 1), days=5)

        self.assertEqual(len(rec_events), 0)
        self.assertEqual(len(debt_events), 0)
        self.assertTrue(all(val == Decimal("0.00") for _, val in history))

    # ------------------------------------------------------------------
    # 5. Fixed Query Counts (O(1) assertNumQueries)
    # ------------------------------------------------------------------

    def test_recurring_events_query_count_is_fixed(self):
        """Chứng minh số query của get_recurring_events KHÔNG tăng khi tăng số giao dịch (2 vs 20)."""
        # Tạo 2 recurring transactions
        for i in range(2):
            base_tx = Transaction.objects.create(
                wallet=self.wallet,
                title=f"Recurring {i}",
                value=Decimal("100000.00"),
                date=datetime.date(2026, 1, 1),
                type="EXPENSE",
                update_wallet=True,
                recurrent=True,
            )
            rec = TransactionRecurrency.objects.create(
                transaction=base_tx,
                amount=1,
                duration="MONTHS",
                active=True,
            )
            base_tx.recurrency = rec
            base_tx.save(update_fields=["recurrency"])

        with self.assertNumQueries(2):
            events_2 = get_recurring_events(
                self.wallet,
                start=datetime.date(2026, 1, 1),
                end=datetime.date(2026, 4, 1),
                today=datetime.date(2026, 1, 1),
            )
        self.assertEqual(len(events_2), 6)

        # Thêm 18 cái nữa (tổng 20)
        for i in range(2, 20):
            base_tx = Transaction.objects.create(
                wallet=self.wallet,
                title=f"Recurring {i}",
                value=Decimal("100000.00"),
                date=datetime.date(2026, 1, 1),
                type="EXPENSE",
                update_wallet=True,
                recurrent=True,
            )
            rec = TransactionRecurrency.objects.create(
                transaction=base_tx,
                amount=1,
                duration="MONTHS",
                active=True,
            )
            base_tx.recurrency = rec
            base_tx.save(update_fields=["recurrency"])

        with self.assertNumQueries(2):
            events_20 = get_recurring_events(
                self.wallet,
                start=datetime.date(2026, 1, 1),
                end=datetime.date(2026, 4, 1),
                today=datetime.date(2026, 1, 1),
            )
        self.assertEqual(len(events_20), 60)

    def test_debt_events_query_count_is_fixed(self):
        """Chứng minh số query của get_debt_events KHÔNG tăng khi tăng số hợp đồng (2 vs 20)."""
        # Tạo 2 debt loans kèm payments
        for i in range(2):
            d = DebtLoan.objects.create(
                wallet=self.wallet,
                person_name=f"Person {i}",
                type="DEBT_BORROWED",
                principal_amount=Decimal("5000000.00"),
                start_date=datetime.date(2026, 1, 1),
                due_date=datetime.date(2026, 2, 1),
                status="ACTIVE",
            )
            DebtPayment.objects.create(
                debt=d,
                amount=Decimal("1000000.00"),
                date=datetime.date(2026, 1, 10),
                update_wallet=False,
            )

        with self.assertNumQueries(2):
            debt_events_2 = get_debt_events(
                self.wallet,
                start=datetime.date(2026, 1, 1),
                end=datetime.date(2026, 3, 1),
                today=datetime.date(2026, 1, 1),
            )
        self.assertEqual(len(debt_events_2), 2)

        # Thêm 18 hợp đồng nữa (tổng 20)
        for i in range(2, 20):
            d = DebtLoan.objects.create(
                wallet=self.wallet,
                person_name=f"Person {i}",
                type="DEBT_BORROWED",
                principal_amount=Decimal("5000000.00"),
                start_date=datetime.date(2026, 1, 1),
                due_date=datetime.date(2026, 2, 1),
                status="ACTIVE",
            )
            DebtPayment.objects.create(
                debt=d,
                amount=Decimal("1000000.00"),
                date=datetime.date(2026, 1, 10),
                update_wallet=False,
            )

        with self.assertNumQueries(2):
            debt_events_20 = get_debt_events(
                self.wallet,
                start=datetime.date(2026, 1, 1),
                end=datetime.date(2026, 3, 1),
                today=datetime.date(2026, 1, 1),
            )
        self.assertEqual(len(debt_events_20), 20)

    def test_daily_variable_spending_query_count_is_fixed(self):
        """Chứng minh số query của get_daily_variable_spending KHÔNG tăng khi tăng số giao dịch (2 vs 20)."""
        end_date = datetime.date(2026, 2, 28)
        for i in range(2):
            Transaction.objects.create(
                wallet=self.wallet,
                title=f"Expense {i}",
                value=Decimal("50000.00"),
                date=end_date,
                type="EXPENSE",
                update_wallet=True,
                recurrent=False,
            )

        with self.assertNumQueries(1):
            get_daily_variable_spending(self.wallet, end=end_date, days=60)

        # Thêm 18 giao dịch nữa
        for i in range(2, 20):
            Transaction.objects.create(
                wallet=self.wallet,
                title=f"Expense {i}",
                value=Decimal("50000.00"),
                date=end_date,
                type="EXPENSE",
                update_wallet=True,
                recurrent=False,
            )

        with self.assertNumQueries(1):
            get_daily_variable_spending(self.wallet, end=end_date, days=60)

    # ------------------------------------------------------------------
    # 6. get_forecast_inputs tests
    # ------------------------------------------------------------------

    def test_forecast_inputs_days_validation(self):
        """Kiểm tra tham số days chỉ nhận 30, 60, 90 (raise ValueError nếu khác)."""
        for invalid_days in [0, 15, 45, 100, -30]:
            with self.assertRaises(ValueError):
                get_forecast_inputs(self.wallet, days=invalid_days)

        for valid_days in [30, 60, 90]:
            res = get_forecast_inputs(self.wallet, days=valid_days)
            self.assertIsInstance(res, ForecastInputs)
            self.assertEqual(res.horizon_end, res.today + datetime.timedelta(days=valid_days))

    def test_forecast_inputs_aggregation_structure(self):
        """get_forecast_inputs gom đúng các dữ liệu và sắp xếp events theo ngày."""
        today = datetime.date(2026, 2, 1)

        # Tạo recurring
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Tien nha",
            value=Decimal("5000000.00"),
            date=datetime.date(2026, 1, 1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        # Tạo debt
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Anh Nam",
            type="DEBT_BORROWED",
            principal_amount=Decimal("3000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 2, 15),
            status="ACTIVE",
        )

        res = get_forecast_inputs(
            self.wallet,
            days=30,
            history_days=10,
            today=today,
        )

        self.assertEqual(res.current_balance, self.wallet.current_amount)
        self.assertEqual(res.today, today)
        self.assertEqual(res.horizon_end, today + datetime.timedelta(days=30))
        self.assertEqual(len(res.events), 3)
        # Recurring occurrence step 1 (2026-02-01) matches today (2026-02-01)
        self.assertEqual(res.events[0].date, datetime.date(2026, 2, 1))
        self.assertEqual(res.events[0].source, "RECURRING")
        # Debt event is 2026-02-15
        self.assertEqual(res.events[1].date, datetime.date(2026, 2, 15))
        self.assertEqual(res.events[1].source, "DEBT")
        # Recurring occurrence step 2 is 2026-03-01 (< 2026-03-03)
        self.assertEqual(res.events[2].date, datetime.date(2026, 3, 1))
        self.assertEqual(res.events[2].source, "RECURRING")
        self.assertEqual(len(res.daily_variable_history), 10)
        # Check dict access / subscripting
        self.assertEqual(res["current_balance"], self.wallet.current_amount)
        self.assertIn("events", res.to_dict())
