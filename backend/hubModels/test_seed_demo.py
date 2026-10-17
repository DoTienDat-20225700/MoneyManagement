import io
import os
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from hubModels.demo_seed import (
    DEMO_USER_SAFE_EMAIL,
    DEMO_USER_STRESSED_EMAIL,
    DemoDataSeeder,
    get_demo_password,
    verify_demo_data,
)
from hubModels.models import (
    CategoryBudget,
    CustomLabel,
    DebtLoan,
    DebtPayment,
    HubUser,
    SavingPlan,
    SavingPlanContribution,
    Transaction,
    Wallet,
)


@override_settings(DEBUG=True)
class SeedDemoCommandTestCase(TestCase):
    """
    Toàn bộ test case kiểm thử cho management command seed_demo và module demo_seed.
    """

    def setUp(self):
        super().setUp()
        self.out = io.StringIO()

    def test_01_seed_demo_creates_both_accounts_and_passes_verification(self):
        """
        Chạy command seed_demo tạo đúng 2 tài khoản, verify_demo_data của cả hai trả rỗng (OK).
        """
        call_command('seed_demo', '--reset', '--yes', stdout=self.out)
        output = self.out.getvalue()
        self.assertIn("KIỂM CHỨNG: OK", output)

        u1 = HubUser.objects.filter(email=DEMO_USER_STRESSED_EMAIL).first()
        u2 = HubUser.objects.filter(email=DEMO_USER_SAFE_EMAIL).first()
        self.assertIsNotNone(u1)
        self.assertIsNotNone(u2)

        violations1 = verify_demo_data(u1)
        violations2 = verify_demo_data(u2)
        self.assertEqual(violations1, [])
        self.assertEqual(violations2, [])

    def test_02_idempotency_without_reset(self):
        """
        Chạy lại không có --reset: không thay đổi dữ liệu, thoát với thông báo cảnh báo.
        Chạy lại với --reset --yes: tạo lại thành công và đạt kiểm chứng.
        """
        # First run
        call_command('seed_demo', '--reset', '--yes', stdout=self.out)
        u1 = HubUser.objects.get(email=DEMO_USER_STRESSED_EMAIL)
        w1 = u1.get_wallet()
        initial_balance = w1.current_amount
        initial_tx_count = w1.transactions.count()

        # Second run without --reset
        out_no_reset = io.StringIO()
        call_command('seed_demo', stdout=out_no_reset)
        output = out_no_reset.getvalue()
        self.assertIn("Dữ liệu demo đã có, dùng --reset để tạo lại", output)

        w1.refresh_from_db()
        self.assertEqual(w1.current_amount, initial_balance)
        self.assertEqual(w1.transactions.count(), initial_tx_count)

        # Third run with --reset --yes
        out_reset = io.StringIO()
        call_command('seed_demo', '--reset', '--yes', stdout=out_reset)
        self.assertIn("KIỂM CHỨNG: OK", out_reset.getvalue())
        u1_new = HubUser.objects.get(email=DEMO_USER_STRESSED_EMAIL)
        self.assertEqual(verify_demo_data(u1_new), [])

    def test_03_data_isolation_does_not_affect_other_users(self):
        """
        Cô lập an toàn: tạo một người dùng khác với giao dịch trước khi chạy --reset;
        sau khi chạy seed_demo --reset --yes, dữ liệu người dùng khác hoàn toàn không đổi.
        """
        other_user = HubUser.objects.create_user(
            email='normal_user@example.com',
            first_name='Văn',
            last_name='Lê',
            password='SecretPassword123!',
        )
        other_wallet = other_user.get_wallet()
        other_wallet.set_balance(Decimal('10000000.00'))

        tx_other = Transaction(
            wallet=other_wallet,
            title='Khoản tiền của người dùng khác',
            value=Decimal('500000.00'),
            type='EXPENSE',
            date=timezone.localdate(),
            update_wallet=True,
        )
        tx_other.save(is_first_save=True)

        other_tx_count = other_wallet.transactions.count()
        other_balance = other_wallet.current_amount

        # Chạy seed_demo với --reset
        call_command('seed_demo', '--reset', '--yes', stdout=self.out)

        # Kiểm tra người dùng khác vẫn nguyên vẹn 100%
        other_user.refresh_from_db()
        other_wallet.refresh_from_db()
        self.assertEqual(other_wallet.current_amount, other_balance)
        self.assertEqual(other_wallet.transactions.count(), other_tx_count)
        self.assertTrue(Transaction.objects.filter(pk=tx_other.pk).exists())

    @override_settings(DEBUG=False)
    def test_04_refuse_when_debug_false_without_force(self):
        """
        Từ chối chạy khi settings.DEBUG = False nếu không có cờ --force.
        Khi có cờ --force thì được phép chạy.
        """
        with self.assertRaises(CommandError) as ctx:
            call_command('seed_demo', '--reset', '--yes', stdout=self.out)
        self.assertIn("LỖI AN TOÀN", str(ctx.exception))

        # Cho phép chạy khi có --force
        call_command('seed_demo', '--reset', '--yes', '--force', stdout=self.out)
        self.assertIn("KIỂM CHỨNG: OK", self.out.getvalue())

    def test_05_reproducibility_with_seed(self):
        """
        Tính tái lập: cùng seed và ngày -> cùng số giao dịch và số dư ví.
        Khác seed -> dữ liệu khác nhưng vẫn đạt kiểm chứng tính nhất quán.
        """
        # Run with seed=2026
        call_command('seed_demo', '--reset', '--yes', '--seed', '2026', stdout=self.out)
        w1_seed1 = HubUser.objects.get(email=DEMO_USER_STRESSED_EMAIL).get_wallet()
        bal1 = w1_seed1.current_amount
        tx_cnt1 = w1_seed1.transactions.count()

        # Re-run with seed=2026
        call_command('seed_demo', '--reset', '--yes', '--seed', '2026', stdout=self.out)
        w1_seed1_again = HubUser.objects.get(email=DEMO_USER_STRESSED_EMAIL).get_wallet()
        self.assertEqual(w1_seed1_again.current_amount, bal1)
        self.assertEqual(w1_seed1_again.transactions.count(), tx_cnt1)

        # Run with different seed=9999
        call_command('seed_demo', '--reset', '--yes', '--seed', '9999', stdout=self.out)
        w1_diff = HubUser.objects.get(email=DEMO_USER_STRESSED_EMAIL).get_wallet()
        # Verify it still passes consistency verification
        violations = verify_demo_data(w1_diff.user)
        self.assertEqual(violations, [])

    def test_06_date_relativity_and_first_half_month_warning(self):
        """
        Tính tương đối theo ngày:
        - Mock date ở nửa sau tháng (ngày 20): F03 và F05 đều đạt kiểm chứng.
        - Mock date ở nửa đầu tháng (ngày 5): in cảnh báo quy tắc F05 rebalance suggestions.
        """
        # Nửa sau tháng: 2026-11-20
        mock_late_date = date(2026, 11, 20)
        with mock.patch('django.utils.timezone.localdate', return_value=mock_late_date):
            out_late = io.StringIO()
            call_command('seed_demo', '--reset', '--yes', stdout=out_late)
            u1 = HubUser.objects.get(email=DEMO_USER_STRESSED_EMAIL)
            violations = verify_demo_data(u1, as_of_date=mock_late_date)
            self.assertEqual(violations, [])
            self.assertIn("KIỂM CHỨNG: OK", out_late.getvalue())

        # Nửa đầu tháng: 2026-12-05
        mock_early_date = date(2026, 12, 5)
        with mock.patch('django.utils.timezone.localdate', return_value=mock_early_date):
            out_early = io.StringIO()
            call_command('seed_demo', '--reset', '--yes', stdout=out_early)
            output = out_early.getvalue()
            self.assertIn("CẢNH BÁO F05: Gợi ý tái cân bằng sẽ trống vì chưa qua nửa tháng", output)

    def test_07_atomic_rollback_on_intermediate_error(self):
        """
        Lỗi giữa chừng trong quá trình seed (ví dụ mock một method ném exception)
        thì transaction rollback hoàn toàn, không để lại dữ liệu dở dang.
        """
        # Make sure demo accounts are cleared initially
        HubUser.objects.filter(email__in=[DEMO_USER_STRESSED_EMAIL, DEMO_USER_SAFE_EMAIL]).delete()

        # Mock an error in _seed_safe_user
        with mock.patch.object(DemoDataSeeder, '_seed_safe_user', side_effect=RuntimeError("Lỗi mô phỏng giữa chừng")):
            with self.assertRaises(RuntimeError):
                call_command('seed_demo', '--reset', '--yes', stdout=self.out)

        # Neither user1 nor user2 should exist
        self.assertFalse(HubUser.objects.filter(email=DEMO_USER_STRESSED_EMAIL).exists())
        self.assertFalse(HubUser.objects.filter(email=DEMO_USER_SAFE_EMAIL).exists())

    def test_08_write_guide_creates_file(self):
        """
        Tùy chọn --write-guide xuất bản hướng dẫn demo chi tiết.
        """
        guide_file = 'test_demo_guide.md'
        try:
            call_command('seed_demo', '--reset', '--yes', '--write-guide', guide_file, stdout=self.out)
            self.assertTrue(os.path.exists(guide_file))
            with open(guide_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertIn("KỊCH BẢN DEMO TỪNG BƯỚC", content)
            self.assertIn(DEMO_USER_STRESSED_EMAIL, content)
            self.assertIn(DEMO_USER_SAFE_EMAIL, content)
        finally:
            if os.path.exists(guide_file):
                os.remove(guide_file)
