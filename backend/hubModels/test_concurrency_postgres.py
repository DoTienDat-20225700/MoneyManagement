import datetime
from decimal import Decimal
import threading
import time
import unittest

from django.core.exceptions import ValidationError
from django.db import connection, transaction as db_transaction
from django.test import TransactionTestCase

from hubModels.factory import TransactionFactory
from hubModels.models import (
    CategoryBudget,
    CustomLabel,
    DebtLoan,
    DebtPayment,
    HubUser,
    Transaction,
    Wallet,
)
from hubAPI.views import TransactionAPIView
from rest_framework.test import APIRequestFactory, force_authenticate


@unittest.skipUnless(
    connection.vendor == "postgresql",
    "Test concurrency chỉ chạy trên PostgreSQL để kiểm chứng khóa dòng và thứ tự khóa thực tế."
)
class PostgresConcurrencyTestCase(TransactionTestCase):
    """
    Bộ kiểm thử đồng thời (Concurrency) trên PostgreSQL:
    1. Kế thừa TransactionTestCase để dữ liệu được commit thật sự vào PostgreSQL,
       cho phép các worker thread riêng biệt nhìn thấy dữ liệu qua các connection độc lập.
    2. Sử dụng threading.Barrier để đồng bộ thời điểm xuất phát của các thread.
    3. Mỗi thread tự quản lý đóng connection bằng connection.close() khi hoàn tất.
    4. join có timeout để phát hiện Deadlock (nếu có deadlock không được giải tỏa, timeout = fail).
    """

    def setUp(self):
        self.factory = TransactionFactory()

    def test_a_concurrent_payments_no_overpayment_and_wallet_consistent(self):
        """
        a) N thanh toán đồng thời cùng một DebtLoan:
           - Tổng đã trả không vượt remaining ban đầu.
           - Số dư ví = ban đầu trừ (hoặc cộng) đúng tổng các khoản thành công.
           - Không khoản nào bị tính hai lần.
           - Lặp 20 vòng kiểm chứng tính ổn định (không flaky).
        """
        ROUNDS = 20
        N_THREADS = 5
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet = user.get_wallet()
            # Ví có 10.000.000đ
            wallet.set_balance(Decimal('10000000.00'))

            # Cho vay 1.000.000đ (update_wallet=True) -> ví bị trừ 1.000.000đ, còn 9.000.000đ
            debt = DebtLoan.create_from_json({
                'person_name': f'Vay no Round {r}',
                'type': 'LOAN_GIVEN',
                'principal_amount': '1000000.00',
                'update_wallet': True,
            }, user_pk=user.pk)

            wallet.refresh_from_db()
            bal_after_loan = wallet.current_amount
            self.assertEqual(bal_after_loan, Decimal('9000000.00'))
            self.assertEqual(debt.get_remaining_amount(), Decimal('1000000.00'))

            # N_THREADS = 5, mỗi thread cố thu hồi 300.000đ
            # 5 * 300.000 = 1.500.000đ > 1.000.000đ
            # Tối đa chỉ 3 thread có thể thành công (3 * 300k = 900k, còn 100k -> 2 thread sau phải bị chặn)
            barrier = threading.Barrier(N_THREADS)
            results = []
            validation_errors = []
            unexpected_errors = []
            state_lock = threading.Lock()

            def pay_worker():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    p = DebtPayment.create_from_json(debt.pk, user, {
                        'amount': '300000.00',
                        'update_wallet': True,
                    })
                    with state_lock:
                        results.append(p)
                except ValidationError as ve:
                    with state_lock:
                        validation_errors.append(ve)
                except Exception as e:
                    with state_lock:
                        unexpected_errors.append(e)
                finally:
                    connection.close()

            threads = [threading.Thread(target=pay_worker) for _ in range(N_THREADS)]
            for t in threads:
                t.start()

            for t in threads:
                t.join(timeout=10.0)
                if t.is_alive():
                    self.fail(f"Round {r}: Deadlock phát hiện - worker thread không kết thúc trong 10s!")

            self.assertEqual(len(unexpected_errors), 0, f"Lỗi không mong muốn: {unexpected_errors}")
            self.assertEqual(len(results) + len(validation_errors), N_THREADS)

            debt.refresh_from_db()
            wallet.refresh_from_db()

            # Bất biến 1: Tổng đã trả không vượt quá 1.000.000đ
            self.assertLessEqual(debt.get_total_paid(), Decimal('1000000.00'))
            # Bất biến 2: Số lần thành công <= 3
            self.assertLessEqual(len(results), 3)
            # Bất biến 3: Dư nợ còn lại khớp chính xác
            expected_paid = Decimal('300000.00') * len(results)
            self.assertEqual(debt.get_total_paid(), expected_paid)
            # Bất biến 4: Số dư ví tăng đúng bằng tổng tiền các lần thu hồi thành công
            self.assertEqual(wallet.current_amount, bal_after_loan + expected_paid)
            # Bất biến 5: Không có khoản thanh toán nào bị ghi nhận thừa trong DB
            self.assertEqual(debt.payments.count(), len(results))

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_b1_opposite_transfers_no_deadlock_and_balance_conserved(self):
        """
        b1) Sửa giao dịch chuyển ví A->B và B->A chạy song song:
            - Hai thao tác ngược chiều khóa hai ví.
            - Nhờ thứ tự khóa order_by('pk'), khẳng định không có deadlock (không OperationalError).
            - Tổng số dư hai ví A + B được bảo toàn 100%.
            - Lặp 20 vòng.
        """
        ROUNDS = 20
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            # Ví 1
            wallet_1 = user.get_wallet()
            wallet_1.set_balance(Decimal('5000000.00'))

            # Ví 2 (tạo thêm ví cho cùng user)
            wallet_2 = Wallet.objects.create(user=user, current_amount=Decimal('5000000.00'))

            # Tx1 ở Ví 1: Khoản chi 400.000đ có update_wallet -> ví 1 còn 4.600.000đ
            tx1 = Transaction(
                wallet=wallet_1,
                title='Tx from W1',
                value=Decimal('400000.00'),
                type='EXPENSE',
                date=datetime.date.today(),
                update_wallet=True,
            )
            tx1.save(is_first_save=True)

            # Tx2 ở Ví 2: Khoản chi 400.000đ có update_wallet -> ví 2 còn 4.600.000đ
            tx2 = Transaction(
                wallet=wallet_2,
                title='Tx from W2',
                value=Decimal('400000.00'),
                type='EXPENSE',
                date=datetime.date.today(),
                update_wallet=True,
            )
            tx2.save(is_first_save=True)

            wallet_1.refresh_from_db()
            wallet_2.refresh_from_db()
            initial_total = wallet_1.current_amount + wallet_2.current_amount
            self.assertEqual(initial_total, Decimal('9200000.00'))

            # Thread 1: Chuyển Tx1 từ Ví 1 sang Ví 2
            # Thread 2: Chuyển Tx2 từ Ví 2 sang Ví 1
            barrier = threading.Barrier(2)
            errors = []
            state_lock = threading.Lock()

            def worker_transfer_1_to_2():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    Transaction.update_from_json(tx1.pk, user, {'wallet_id': wallet_2.pk})
                except Exception as e:
                    with state_lock:
                        errors.append(('T1', e))
                finally:
                    connection.close()

            def worker_transfer_2_to_1():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    Transaction.update_from_json(tx2.pk, user, {'wallet_id': wallet_1.pk})
                except Exception as e:
                    with state_lock:
                        errors.append(('T2', e))
                finally:
                    connection.close()

            t1 = threading.Thread(target=worker_transfer_1_to_2)
            t2 = threading.Thread(target=worker_transfer_2_to_1)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện khi chuyển ví ngược chiều!")

            self.assertEqual(len(errors), 0, f"Lỗi deadlock hoặc bất thường: {errors}")

            wallet_1.refresh_from_db()
            wallet_2.refresh_from_db()
            final_total = wallet_1.current_amount + wallet_2.current_amount
            # Tổng số dư phải bảo toàn
            self.assertEqual(final_total, initial_total)

            tx1.refresh_from_db()
            tx2.refresh_from_db()
            self.assertEqual(tx1.wallet_id, wallet_2.pk)
            self.assertEqual(tx2.wallet_id, wallet_1.pk)

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_b2_opposite_budget_rebalance_no_deadlock_and_total_conserved(self):
        """
        b2) Tái cân bằng ngân sách ngược chiều X->Y và Y->X chạy song song:
            - Nhờ CategoryBudget.objects.select_for_update().order_by('pk'),
              khẳng định không xảy ra deadlock (không OperationalError).
            - Tổng hạn mức hai ngân sách được bảo toàn tuyệt đối.
            - Lặp 20 vòng.
        """
        ROUNDS = 20
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet = user.get_wallet()
            lbl_x = CustomLabel.objects.create(wallet=wallet, name=f'CatX_{r}', color='#111111')
            lbl_y = CustomLabel.objects.create(wallet=wallet, name=f'CatY_{r}', color='#222222')

            bx = CategoryBudget.objects.create(
                wallet=wallet, label=lbl_x, amount=Decimal('2000000.00'), month=10, year=2026
            )
            by = CategoryBudget.objects.create(
                wallet=wallet, label=lbl_y, amount=Decimal('2000000.00'), month=10, year=2026
            )
            total_budget_before = bx.amount + by.amount

            # Thread 1: Chuyển 200.000đ từ X sang Y
            # Thread 2: Chuyển 200.000đ từ Y sang X
            barrier = threading.Barrier(2)
            errors = []
            state_lock = threading.Lock()

            def rebalance_logic(from_lbl_id, to_lbl_id, amt):
                with db_transaction.atomic():
                    budgets = list(
                        CategoryBudget.objects.select_for_update()
                        .filter(wallet=wallet, month=10, year=2026, label_id__in=[from_lbl_id, to_lbl_id])
                        .order_by('pk')
                    )
                    from_b = next((b for b in budgets if b.label_id == from_lbl_id), None)
                    to_b = next((b for b in budgets if b.label_id == to_lbl_id), None)
                    if from_b.amount - amt < from_b.get_spent():
                        raise ValidationError("Spent exceeds new amount")
                    from_b.amount -= amt
                    to_b.amount += amt
                    from_b.save(update_fields=['amount'])
                    to_b.save(update_fields=['amount'])

            def worker_x_to_y():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    rebalance_logic(lbl_x.id, lbl_y.id, Decimal('200000.00'))
                except Exception as e:
                    with state_lock:
                        errors.append(('X->Y', e))
                finally:
                    connection.close()

            def worker_y_to_x():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    rebalance_logic(lbl_y.id, lbl_x.id, Decimal('200000.00'))
                except Exception as e:
                    with state_lock:
                        errors.append(('Y->X', e))
                finally:
                    connection.close()

            t1 = threading.Thread(target=worker_x_to_y)
            t2 = threading.Thread(target=worker_y_to_x)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện khi rebalance ngược chiều!")

            self.assertEqual(len(errors), 0, f"Lỗi deadlock hoặc bất thường: {errors}")

            bx.refresh_from_db()
            by.refresh_from_db()
            total_budget_after = bx.amount + by.amount
            self.assertEqual(total_budget_after, total_budget_before)
            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_c_concurrent_payment_vs_update_or_delete_debt(self):
        """
        c) Thanh toán nợ đồng thời với sửa/xóa chính DebtLoan đó:
           - Kết quả cuối cùng luôn nhất quán: số dư ví khớp chính xác tổng các payment còn tồn tại.
           - Lặp 20 vòng (10 vòng payment vs update, 10 vòng payment vs delete).
        """
        ROUNDS = 20
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet = user.get_wallet()
            wallet.set_balance(Decimal('10000000.00'))

            debt = DebtLoan.create_from_json({
                'person_name': f'Partner {r}',
                'type': 'LOAN_GIVEN',
                'principal_amount': '5000000.00',
                'update_wallet': True,
            }, user_pk=user.pk)

            wallet.refresh_from_db()
            bal_after_loan = wallet.current_amount
            self.assertEqual(bal_after_loan, Decimal('5000000.00'))

            is_delete_round = (r % 2 == 1)
            barrier = threading.Barrier(2)
            errors = []
            pay_success = False
            mutation_success = False
            state_lock = threading.Lock()

            def payment_thread():
                nonlocal pay_success
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    DebtPayment.create_from_json(debt.pk, user, {
                        'amount': '1000000.00',
                        'update_wallet': True,
                    })
                    with state_lock:
                        pay_success = True
                except (DebtLoan.DoesNotExist, ValidationError) as expected_err:
                    # Nếu delete chạy trước, debt không còn tồn tại -> hợp lệ
                    pass
                except Exception as e:
                    with state_lock:
                        errors.append(('Pay', e))
                finally:
                    connection.close()

            def mutation_thread():
                nonlocal mutation_success
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    if is_delete_round:
                        debt.delete()
                    else:
                        DebtLoan.update_from_json(debt.pk, user, {
                            'person_name': f'Partner Updated {r}',
                        })
                    with state_lock:
                        mutation_success = True
                except Exception as e:
                    with state_lock:
                        errors.append(('Mutation', e))
                finally:
                    connection.close()

            t1 = threading.Thread(target=payment_thread)
            t2 = threading.Thread(target=mutation_thread)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện giữa payment và update/delete debt!")

            self.assertEqual(len(errors), 0, f"Lỗi không mong muốn: {errors}")

            wallet.refresh_from_db()

            if is_delete_round:
                # Nếu là vòng xóa: DebtLoan đã bị xóa
                # Số dư ví phải quay về đúng 10.000.000đ (hoàn trả nợ gốc và hoàn trả payment nếu có)
                self.assertFalse(DebtLoan.objects.filter(pk=debt.pk).exists())
                self.assertEqual(DebtPayment.objects.filter(debt_id=debt.pk).count(), 0)
                self.assertEqual(wallet.current_amount, Decimal('10000000.00'))
            else:
                # Nếu là vòng update: DebtLoan vẫn tồn tại
                self.assertTrue(mutation_success)
                debt.refresh_from_db()
                self.assertEqual(debt.person_name, f'Partner Updated {r}')
                if pay_success:
                    self.assertEqual(wallet.current_amount, bal_after_loan + Decimal('1000000.00'))
                    self.assertEqual(debt.payments.count(), 1)
                else:
                    self.assertEqual(wallet.current_amount, bal_after_loan)
                    self.assertEqual(debt.payments.count(), 0)

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_d_concurrent_delete_same_debtloan_reverses_balance_exactly_once(self):
        """
        d) Hai luồng cùng gọi delete() trên cùng một DebtLoan (đã có hoặc chưa có payment):
           - Khóa thống nhất Wallet -> DebtLoan (check existence sau khóa).
           - Đúng 1 luồng xóa thành công, luồng kia nhận DoesNotExist.
           - Tuyệt đối không hoàn tiền ví lần hai (số dư ví hoàn đúng 1 lần).
           - Chạy lặp 20 vòng (luân phiên có payment và chưa có payment).
        """
        ROUNDS = 20
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet = user.get_wallet()
            wallet.set_balance(Decimal('10000000.00'))

            # Tạo hợp đồng cho vay 2.000.000đ
            debt = DebtLoan.create_from_json({
                'person_name': f'Borrower Round {r}',
                'type': 'LOAN_GIVEN',
                'principal_amount': '2000000.00',
                'interest_rate': '0',
                'duration': 12,
                'started_date': str(datetime.date.today()),
                'update_wallet': True,
            }, user_pk=user.pk)

            wallet.refresh_from_db()
            self.assertEqual(wallet.current_amount, Decimal('8000000.00'))

            has_payment = (r % 2 == 1)
            if has_payment:
                # Vòng lẻ: Có 1 khoản trả nợ 500.000đ với update_wallet=True
                DebtPayment.create_from_json(debt.pk, user, {
                    'amount': '500000.00',
                    'date': str(datetime.date.today()),
                    'update_wallet': True,
                })
                wallet.refresh_from_db()
                self.assertEqual(wallet.current_amount, Decimal('8500000.00'))

            # Hai luồng cùng gọi debt.delete()
            barrier = threading.Barrier(2)
            errors = []
            results = {'success': 0, 'not_found': 0}
            state_lock = threading.Lock()

            def worker():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    debt.delete()
                    with state_lock:
                        results['success'] += 1
                except (DebtLoan.DoesNotExist, ValidationError):
                    with state_lock:
                        results['not_found'] += 1
                except Exception as e:
                    with state_lock:
                        errors.append(e)
                finally:
                    connection.close()

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện khi 2 luồng cùng xóa DebtLoan!")

            self.assertEqual(len(errors), 0, f"Round {r}: Lỗi bất thường: {errors}")
            # Chính xác 1 luồng thành công, 1 luồng nhận DoesNotExist
            self.assertEqual(results['success'], 1, f"Round {r}: Số luồng thành công phải là 1, thực tế: {results['success']}")
            self.assertEqual(results['not_found'], 1, f"Round {r}: Số luồng nhận lỗi phải là 1, thực tế: {results['not_found']}")

            # Kiểm tra DB: DebtLoan đã bị xóa hoàn toàn
            self.assertFalse(DebtLoan.objects.filter(pk=debt.pk).exists())
            self.assertEqual(DebtPayment.objects.filter(debt_id=debt.pk).count(), 0)

            # Bất biến cốt lõi: Số dư ví phải hoàn đúng 1 lần về lại 10.000.000đ!
            # Nếu hoàn tiền kép, số dư sẽ là 12.000.000đ (không payment) hoặc sai lệch.
            wallet.refresh_from_db()
            self.assertEqual(
                wallet.current_amount,
                Decimal('10000000.00'),
                f"Round {r}: Số dư ví bị sai sau khi xóa kép (có thể bị hoàn tiền lần hai)! Thực tế: {wallet.current_amount}"
            )

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_e_concurrent_update_same_wallet_transactions_no_deadlock_and_balance_correct(self):
        """
        e) Sửa giao dịch trong cùng một ví từ hai luồng song song:
           - Hai luồng cùng sửa hai transaction khác nhau thuộc cùng một ví.
           - Đảm bảo không deadlock.
           - Số dư ví cuối cùng phản ánh chính xác cả 2 cập nhật.
           - Lặp 20 vòng.
        """
        ROUNDS = 20
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet = user.get_wallet()
            wallet.set_balance(Decimal('10000000.00'))

            # Tạo tx1 và tx2
            tx1 = Transaction(
                wallet=wallet,
                title=f'Tx1_{r}',
                value=Decimal('200000.00'),
                type='EXPENSE',
                date=datetime.date.today(),
                update_wallet=True,
            )
            tx1.save(is_first_save=True)

            tx2 = Transaction(
                wallet=wallet,
                title=f'Tx2_{r}',
                value=Decimal('300000.00'),
                type='EXPENSE',
                date=datetime.date.today(),
                update_wallet=True,
            )
            tx2.save(is_first_save=True)

            wallet.refresh_from_db()
            self.assertEqual(wallet.current_amount, Decimal('9500000.00'))

            barrier = threading.Barrier(2)
            errors = []
            state_lock = threading.Lock()

            def worker_update_tx1():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    Transaction.update_from_json(tx1.pk, user, {
                        'value': '500000.00',
                        'title': f'Tx1_Updated_{r}',
                    })
                except Exception as e:
                    with state_lock:
                        errors.append(('T1', e))
                finally:
                    connection.close()

            def worker_update_tx2():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    Transaction.update_from_json(tx2.pk, user, {
                        'value': '700000.00',
                        'title': f'Tx2_Updated_{r}',
                    })
                except Exception as e:
                    with state_lock:
                        errors.append(('T2', e))
                finally:
                    connection.close()

            t1 = threading.Thread(target=worker_update_tx1)
            t2 = threading.Thread(target=worker_update_tx2)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện khi sửa giao dịch cùng ví song song!")

            self.assertEqual(len(errors), 0, f"Round {r}: Lỗi xảy ra: {errors}")

            # Kiểm tra trạng thái giao dịch
            tx1.refresh_from_db()
            tx2.refresh_from_db()
            self.assertEqual(tx1.value, Decimal('500000.00'))
            self.assertEqual(tx2.value, Decimal('700000.00'))
            self.assertEqual(tx1.title, f'Tx1_Updated_{r}')
            self.assertEqual(tx2.title, f'Tx2_Updated_{r}')

            # Kiểm tra số dư ví:
            # Ban đầu: 10.000.000
            # Tx1 chi 500.000, Tx2 chi 700.000
            # Số dư ví = 10.000.000 - 500.000 - 700.000 = 8.800.000
            wallet.refresh_from_db()
            self.assertEqual(
                wallet.current_amount,
                Decimal('8800000.00'),
                f"Round {r}: Số dư ví không đúng sau 2 cập nhật song song: {wallet.current_amount}"
            )

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_f_concurrent_delete_vs_wallet_switch(self):
        """
        f) Hai luồng đua giữa delete() và đổi ví của DebtLoan:
           - Luồng 1 gọi delete() trên instance trỏ ví cũ.
           - Luồng 2 đổi ví của hợp đồng sang ví mới.
           - Sau khi khóa DebtLoan, nếu debt.wallet_id != wallet.pk thì ném ValidationError,
             tuyệt đối không hoàn tiền vào ví cũ.
           - Nếu Luồng 1 xóa trước, Luồng 2 nhận DoesNotExist và ví cũ hoàn đúng 1 lần.
           - Chạy lặp 20 vòng, bảo đảm toàn vẹn số dư.
        """
        ROUNDS = 20
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet_1 = user.get_wallet()
            wallet_1.set_balance(Decimal('5000000.00'))

            # Tạo hợp đồng cho vay 1.000.000đ trên wallet_1
            debt = DebtLoan.create_from_json({
                'person_name': f'Borrower Switch {r}',
                'type': 'LOAN_GIVEN',
                'principal_amount': '1000000.00',
                'interest_rate': '0',
                'duration': 12,
                'started_date': str(datetime.date.today()),
                'update_wallet': True,
            }, user_pk=user.pk)

            # Tạo ví 2 cho cùng user
            wallet_2 = Wallet.objects.create(user=user, current_amount=Decimal('5000000.00'))

            wallet_1.refresh_from_db()
            self.assertEqual(wallet_1.current_amount, Decimal('4000000.00'))
            self.assertEqual(wallet_2.current_amount, Decimal('5000000.00'))

            stale_debt_instance = DebtLoan.objects.get(pk=debt.pk)
            self.assertEqual(stale_debt_instance.wallet_id, wallet_1.pk)

            barrier = threading.Barrier(2)
            errors = []
            results = {'deleted': 0, 'validation_error': 0, 'switched': 0, 'switch_missed': 0}
            state_lock = threading.Lock()

            def worker_delete():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    stale_debt_instance.delete()
                    with state_lock:
                        results['deleted'] += 1
                except ValidationError:
                    with state_lock:
                        results['validation_error'] += 1
                except Exception as e:
                    with state_lock:
                        errors.append(('Delete', e))
                finally:
                    connection.close()

            def worker_switch_wallet():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    with db_transaction.atomic():
                        w2 = Wallet.objects.select_for_update().get(pk=wallet_2.pk)
                        d = DebtLoan.objects.select_for_update().get(pk=debt.pk)
                        d.wallet = w2
                        d.save(update_fields=['wallet'])
                    with state_lock:
                        results['switched'] += 1
                except DebtLoan.DoesNotExist:
                    with state_lock:
                        results['switch_missed'] += 1
                except Exception as e:
                    with state_lock:
                        errors.append(('Switch', e))
                finally:
                    connection.close()

            t1 = threading.Thread(target=worker_delete)
            t2 = threading.Thread(target=worker_switch_wallet)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện giữa delete và switch wallet!")

            self.assertEqual(len(errors), 0, f"Round {r}: Lỗi xảy ra: {errors}")

            wallet_1.refresh_from_db()
            wallet_2.refresh_from_db()

            if results['switched'] == 1:
                # Nếu đổi ví thành công: delete() trên instance cũ PHẢI bị chặn bởi ValidationError
                self.assertEqual(
                    results['validation_error'], 1,
                    f"Round {r}: delete() phải bị ValidationError khi ví đã đổi! Kết quả: {results}"
                )
                # wallet_1 tuyệt đối không được hoàn tiền sai ví (phải giữ nguyên 4.000.000đ)
                self.assertEqual(
                    wallet_1.current_amount,
                    Decimal('4000000.00'),
                    f"Round {r}: wallet_1 bị hoàn tiền sai ví! Hiện tại: {wallet_1.current_amount}"
                )
                # wallet_2 vẫn giữ nguyên 5.000.000đ
                self.assertEqual(wallet_2.current_amount, Decimal('5000000.00'))
                # Hợp đồng vẫn tồn tại trong DB thuộc về wallet_2
                self.assertTrue(DebtLoan.objects.filter(pk=debt.pk, wallet=wallet_2).exists())
            else:
                # Nếu delete() chạy trước: Luồng xóa thành công, Luồng switch bỏ lỡ (DoesNotExist)
                self.assertEqual(results['deleted'], 1)
                self.assertEqual(results['switch_missed'], 1)
                # wallet_1 được hoàn đúng 1.000.000đ về 5.000.000đ
                self.assertEqual(wallet_1.current_amount, Decimal('5000000.00'))
                self.assertEqual(wallet_2.current_amount, Decimal('5000000.00'))
                # Hợp đồng đã bị xóa khỏi DB
                self.assertFalse(DebtLoan.objects.filter(pk=debt.pk).exists())

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)

    def test_g_concurrent_delete_vs_update_same_transaction(self):
        """
        g) Thử tái hiện deadlock xóa-vs-sửa trên cùng một giao dịch (50 vòng):
           - Luồng 1: TransactionAPIView.delete(tx.pk).
           - Luồng 2: Transaction.update_from_json(tx.pk, user, {'value': '800000.00'}).
           - Kiểm tra xem có deadlock (OperationalError) hoặc sai số dư ví hay không.
           - Lặp 50 vòng.
        """
        ROUNDS = 50
        pass_count = 0

        for r in range(ROUNDS):
            user = self.factory.create_user()
            wallet = user.get_wallet()
            wallet.set_balance(Decimal('10000000.00'))

            tx = Transaction(
                wallet=wallet,
                title=f'Tx_Del_vs_Upd_{r}',
                value=Decimal('500000.00'),
                type='EXPENSE',
                date=datetime.date.today(),
                update_wallet=True,
            )
            tx.save(is_first_save=True)

            wallet.refresh_from_db()
            self.assertEqual(wallet.current_amount, Decimal('9500000.00'))

            barrier = threading.Barrier(2)
            errors = []
            results = {'del_status': [], 'update_status': []}
            state_lock = threading.Lock()

            def worker_delete():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    factory = APIRequestFactory()
                    request = factory.delete(f'/api/transaction/{tx.pk}/')
                    force_authenticate(request, user=user)
                    view = TransactionAPIView.as_view()
                    response = view(request, transaction_pk=tx.pk)
                    with state_lock:
                        results['del_status'].append(response.status_code)
                except Exception as e:
                    with state_lock:
                        errors.append(('Delete', e))
                finally:
                    connection.close()

            def worker_update():
                connection.close()
                try:
                    barrier.wait(timeout=5.0)
                    Transaction.update_from_json(tx.pk, user, {
                        'value': '800000.00',
                        'title': f'Tx_Updated_{r}',
                    })
                    with state_lock:
                        results['update_status'].append('SUCCESS')
                except Transaction.DoesNotExist:
                    with state_lock:
                        results['update_status'].append('NOT_FOUND')
                except Exception as e:
                    with state_lock:
                        errors.append(('Update', e))
                finally:
                    connection.close()

            t1 = threading.Thread(target=worker_delete)
            t2 = threading.Thread(target=worker_update)

            t1.start()
            t2.start()

            t1.join(timeout=10.0)
            t2.join(timeout=10.0)

            if t1.is_alive() or t2.is_alive():
                self.fail(f"Round {r}: Deadlock phát hiện giữa TransactionAPIView.delete và update_from_json!")

            self.assertEqual(len(errors), 0, f"Round {r}: Lỗi bất thường: {errors}")

            wallet.refresh_from_db()
            # Bất biến: Sau khi một luồng xóa giao dịch thành công (status 200),
            # toàn bộ tiền chi tiêu phải được hoàn lại ví đầy đủ (về 10.000.000đ).
            self.assertEqual(
                wallet.current_amount,
                Decimal('10000000.00'),
                f"Round {r}: Số dư ví bị sai sau khi xóa và sửa đồng thời! Ví hiện tại: {wallet.current_amount}"
            )
            # Giao dịch không còn tồn tại trong DB
            self.assertFalse(Transaction.objects.filter(pk=tx.pk).exists())

            pass_count += 1

        self.assertEqual(pass_count, ROUNDS)
