from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from hubModels.models import (
    HubUser, Wallet, CustomLabel, Transaction, TransactionRecurrency,
    SavingPlan, SavingPlanContribution, CategoryBudget
)


class Command(BaseCommand):
    help = 'Seeds realistic sample financial data for a specified user.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='admin@gmail.com',
            help='User email to seed data for (default: admin@gmail.com).',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing transactions, budgets, saving plans, and labels for this user before seeding.',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        clear_first = options.get('clear')

        try:
            user = HubUser.objects.get(email=email)
        except HubUser.DoesNotExist:
            raise CommandError(f"User with email '{email}' does not exist.")

        wallet = user.get_wallet()
        if not wallet:
            raise CommandError(f"User '{email}' does not have an active wallet.")

        self.stdout.write(f"Seeding demo data for {user.get_full_name() or user.email} (Wallet ID: {wallet.pk})...")

        with db_transaction.atomic():
            if clear_first:
                self.stdout.write("Clearing existing data...")
                SavingPlanContribution.objects.filter(user=user).delete()
                SavingPlan.objects.filter(wallet=wallet).delete()
                CategoryBudget.objects.filter(wallet=wallet).delete()
                Transaction.objects.filter(wallet=wallet).delete()
                CustomLabel.objects.filter(wallet=wallet).delete()

            # 1. Custom Labels / Categories
            labels_data = [
                ("Ăn uống", "#EF4444"),             # Đỏ
                ("Nhà cửa & Tiện ích", "#3B82F6"),    # Xanh dương
                ("Đi lại & Xăng xe", "#F59E0B"),      # Vàng cam
                ("Mua sắm & Tiêu dùng", "#8B5CF6"),   # Tím
                ("Sức khoẻ & Y tế", "#10B981"),       # Xanh ngọc
                ("Giải trí & Cà phê", "#EC4899"),     # Hồng
                ("Học tập & Sách vở", "#06B6D4"),     # Xanh lơ
                ("Tiền lương", "#22C55E"),            # Xanh lá
                ("Thưởng & Đầu tư", "#14B8A6"),       # Teal
            ]

            label_map = {}
            for name, color in labels_data:
                lbl, _ = CustomLabel.objects.get_or_create(wallet=wallet, name=name, defaults={'color': color})
                label_map[name] = lbl

            self.stdout.write(f"✓ Created/verified {len(label_map)} categories.")

            # 2. Historical & Current Transactions (May 2026 to October 2026)
            transactions_data = [
                # --- Tháng 5/2026 ---
                ("Lương tháng 5/2026", Decimal("25000000.00"), "EARNING", date(2026, 5, 5), "Tiền lương", False, False),
                ("Tiền thuê nhà tháng 5", Decimal("6500000.00"), "EXPENSE", date(2026, 5, 6), "Nhà cửa & Tiện ích", True, False),
                ("Điện nước & Internet", Decimal("1150000.00"), "EXPENSE", date(2026, 5, 10), "Nhà cửa & Tiện ích", False, True),
                ("Đi siêu thị Mega Market", Decimal("3200000.00"), "EXPENSE", date(2026, 5, 12), "Ăn uống", False, True),
                ("Xăng xe tháng 5", Decimal("850000.00"), "EXPENSE", date(2026, 5, 20), "Đi lại & Xăng xe", False, False),
                ("Cà phê cuối tuần", Decimal("450000.00"), "EXPENSE", date(2026, 5, 25), "Giải trí & Cà phê", False, False),

                # --- Tháng 6/2026 ---
                ("Lương tháng 6/2026", Decimal("25000000.00"), "EARNING", date(2026, 6, 5), "Tiền lương", False, False),
                ("Thưởng dự án Q2", Decimal("6000000.00"), "EARNING", date(2026, 6, 15), "Thưởng & Đầu tư", False, False),
                ("Tiền thuê nhà tháng 6", Decimal("6500000.00"), "EXPENSE", date(2026, 6, 6), "Nhà cửa & Tiện ích", True, False),
                ("Mua quần áo mùa hè Uniqlo", Decimal("2800000.00"), "EXPENSE", date(2026, 6, 18), "Mua sắm & Tiêu dùng", False, True),
                ("Ăn uống & Tiệc sinh nhật", Decimal("4100000.00"), "EXPENSE", date(2026, 6, 22), "Ăn uống", False, False),
                ("Khám nha khoa định kỳ", Decimal("1500000.00"), "EXPENSE", date(2026, 6, 28), "Sức khoẻ & Y tế", False, False),

                # --- Tháng 7/2026 ---
                ("Lương tháng 7/2026", Decimal("25000000.00"), "EARNING", date(2026, 7, 5), "Tiền lương", False, False),
                ("Tiền thuê nhà tháng 7", Decimal("6500000.00"), "EXPENSE", date(2026, 7, 6), "Nhà cửa & Tiện ích", True, False),
                ("Mua khoá học AWS Cloud", Decimal("2200000.00"), "EXPENSE", date(2026, 7, 14), "Học tập & Sách vở", False, False),
                ("Tiền điện mùa nóng", Decimal("1650000.00"), "EXPENSE", date(2026, 7, 15), "Nhà cửa & Tiện ích", False, True),
                ("Ăn uống nhà hàng & cafe", Decimal("3800000.00"), "EXPENSE", date(2026, 7, 25), "Ăn uống", False, False),

                # --- Tháng 8/2026 ---
                ("Lương tháng 8/2026", Decimal("26500000.00"), "EARNING", date(2026, 8, 5), "Tiền lương", False, False),
                ("Cổ tức đầu tư chứng khoán", Decimal("4500000.00"), "EARNING", date(2026, 8, 12), "Thưởng & Đầu tư", False, False),
                ("Tiền thuê nhà tháng 8", Decimal("6500000.00"), "EXPENSE", date(2026, 8, 6), "Nhà cửa & Tiện ích", True, False),
                ("Bảo dưỡng xe máy Honda", Decimal("1250000.00"), "EXPENSE", date(2026, 8, 16), "Đi lại & Xăng xe", False, False),
                ("Mua sách chuyên ngành IT", Decimal("950000.00"), "EXPENSE", date(2026, 8, 20), "Học tập & Sách vở", False, False),
                ("Ăn uống hàng ngày", Decimal("3600000.00"), "EXPENSE", date(2026, 8, 28), "Ăn uống", False, False),

                # --- Tháng 9/2026 ---
                ("Lương tháng 9/2026", Decimal("26500000.00"), "EARNING", date(2026, 9, 5), "Tiền lương", False, False),
                ("Lợi nhuận dự án Freelance", Decimal("8000000.00"), "EARNING", date(2026, 9, 20), "Thưởng & Đầu tư", False, False),
                ("Tiền thuê nhà tháng 9", Decimal("6500000.00"), "EXPENSE", date(2026, 9, 6), "Nhà cửa & Tiện ích", True, False),
                ("Mua màn hình làm việc 4K", Decimal("7200000.00"), "EXPENSE", date(2026, 9, 15), "Mua sắm & Tiêu dùng", False, True),
                ("Ăn uống & Giao lưu", Decimal("4200000.00"), "EXPENSE", date(2026, 9, 26), "Ăn uống", False, False),
                ("Gói tập Gym 6 tháng", Decimal("3600000.00"), "EXPENSE", date(2026, 9, 28), "Sức khoẻ & Y tế", False, True),

                # --- Tháng hiện tại (10/2026) ---
                ("Lương tháng 10/2026", Decimal("28000000.00"), "EARNING", date(2026, 10, 5), "Tiền lương", False, False),
                ("Thưởng KPI quý 3", Decimal("7500000.00"), "EARNING", date(2026, 10, 10), "Thưởng & Đầu tư", False, False),
                ("Tiền thuê nhà tháng 10", Decimal("6500000.00"), "EXPENSE", date(2026, 10, 6), "Nhà cửa & Tiện ích", True, False),
                ("Tiền điện nước Internet tháng 10", Decimal("1200000.00"), "EXPENSE", date(2026, 10, 8), "Nhà cửa & Tiện ích", False, True),
                ("Chuyển khoản nạp thẻ VinMart", Decimal("2500000.00"), "EXPENSE", date(2026, 10, 9), "Ăn uống", False, True),
                ("Đi ăn nhà hàng lẩu Haidilao", Decimal("1250000.00"), "EXPENSE", date(2026, 10, 11), "Ăn uống", False, True),
                ("Đổ xăng xe máy", Decimal("1100000.00"), "EXPENSE", date(2026, 10, 12), "Đi lại & Xăng xe", False, False),
                ("Cà phê Highlands & trà sữa", Decimal("1450000.00"), "EXPENSE", date(2026, 10, 13), "Giải trí & Cà phê", False, False),
                ("Mua tai nghe Bluetooth", Decimal("1800000.00"), "EXPENSE", date(2026, 10, 14), "Mua sắm & Tiêu dùng", False, True),
                ("Thuốc bổ & Vitamin D3", Decimal("650000.00"), "EXPENSE", date(2026, 10, 15), "Sức khoẻ & Y tế", False, False),
            ]

            created_tx_count = 0
            for title, val, tx_type, tx_date, lbl_name, is_rec, is_imp in transactions_data:
                tx = Transaction.objects.create(
                    wallet=wallet,
                    title=title,
                    value=val,
                    type=tx_type,
                    date=tx_date,
                    label=label_map.get(lbl_name),
                    recurrent=is_rec,
                    imported=is_imp,
                    update_wallet=False,
                )
                if is_rec:
                    TransactionRecurrency.objects.create(
                        transaction=tx,
                        amount=1,
                        duration='MONTHS',
                        active=True,
                    )
                created_tx_count += 1

            self.stdout.write(f"✓ Created {created_tx_count} sample transactions spanning 6 months.")

            # Set realistic current wallet balance
            wallet.set_balance(Decimal("45680000.00"))
            self.stdout.write(f"✓ Set wallet current balance to 45.680.000 đ.")

            # 3. Monthly Budgets for Current Month (10/2026)
            budgets_setup = [
                # Ăn uống: đã chi 3.750.000 đ -> Ngân sách 4.500.000 đ (83.3% -> Sắp chạm ngưỡng)
                ("Ăn uống", Decimal("4500000.00")),
                # Nhà cửa: đã chi 7.700.000 đ -> Ngân sách 8.000.000 đ (96.3% -> Sắp chạm ngưỡng)
                ("Nhà cửa & Tiện ích", Decimal("8000000.00")),
                # Giải trí: đã chi 1.450.000 đ -> Ngân sách 1.200.000 đ (120.8% -> Vượt ngân sách)
                ("Giải trí & Cà phê", Decimal("1200000.00")),
                # Đi lại: đã chi 1.100.000 đ -> Ngân sách 2.000.000 đ (55.0% -> Bình thường)
                ("Đi lại & Xăng xe", Decimal("2000000.00")),
                # Mua sắm: đã chi 1.800.000 đ -> Ngân sách 3.000.000 đ (60.0% -> Bình thường)
                ("Mua sắm & Tiêu dùng", Decimal("3000000.00")),
                # Sức khoẻ: đã chi 650.000 đ -> Ngân sách 1.500.000 đ (43.3% -> Bình thường)
                ("Sức khoẻ & Y tế", Decimal("1500000.00")),
            ]

            created_budget_count = 0
            for lbl_name, amount in budgets_setup:
                CategoryBudget.objects.create(
                    wallet=wallet,
                    label=label_map[lbl_name],
                    amount=amount,
                    month=10,
                    year=2026,
                )
                created_budget_count += 1

            self.stdout.write(f"✓ Created {created_budget_count} budgets for month 10/2026.")

            # 4. Saving Plans & Realistic Contributions
            # Plan 1: Active Goal with healthy contributions and predictable daily rate
            plan1 = SavingPlan.objects.create(
                wallet=wallet,
                title="Quỹ khẩn cấp 6 tháng",
                amount=Decimal("60000000.00"),
                goal_date=date(2026, 12, 31),
                description="Tích luỹ dự phòng an toàn tài chính tương đương 6 tháng chi tiêu",
                active=True,
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan1, user=user, amount=Decimal("15000000.00"),
                date=date(2026, 7, 10), description="Trích thưởng quý 2"
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan1, user=user, amount=Decimal("10000000.00"),
                date=date(2026, 8, 10), description="Tiết kiệm lương tháng 8"
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan1, user=user, amount=Decimal("10000000.00"),
                date=date(2026, 9, 10), description="Tiết kiệm lương tháng 9"
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan1, user=user, amount=Decimal("10000000.00"),
                date=date(2026, 10, 10), description="Tiết kiệm lương tháng 10"
            )

            # Plan 2: Completed Goal (100% achieved)
            plan2 = SavingPlan.objects.create(
                wallet=wallet,
                title="Mua MacBook Pro M4 Pro",
                amount=Decimal("45000000.00"),
                goal_date=date(2026, 10, 15),
                description="Nâng cấp máy tính phục vụ công việc lập trình",
                active=True,
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan2, user=user, amount=Decimal("15000000.00"),
                date=date(2026, 8, 15), description="Khoản tích luỹ ban đầu"
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan2, user=user, amount=Decimal("15000000.00"),
                date=date(2026, 9, 15), description="Tiền làm thêm dự án freelance"
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan2, user=user, amount=Decimal("15000000.00"),
                date=date(2026, 10, 12), description="Hoàn thành đủ số tiền mua máy!"
            )

            # Plan 3: Recently started Goal
            plan3 = SavingPlan.objects.create(
                wallet=wallet,
                title="Du lịch Nhật Bản ngắm hoa anh đào",
                amount=Decimal("35000000.00"),
                goal_date=date(2027, 4, 1),
                description="Chuyến đi Tokyo & Kyoto cùng gia đình",
                active=True,
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan3, user=user, amount=Decimal("7000000.00"),
                date=date(2026, 10, 8), description="Đặt cọc vé máy bay"
            )

            # Plan 4: Paused / Closed Goal
            plan4 = SavingPlan.objects.create(
                wallet=wallet,
                title="Đổi xe máy mới",
                amount=Decimal("30000000.00"),
                goal_date=date(2027, 6, 30),
                description="Tạm dừng do ưu tiên quỹ khẩn cấp",
                active=False,
            )
            SavingPlanContribution.objects.create(
                saving_plan=plan4, user=user, amount=Decimal("5000000.00"),
                date=date(2026, 6, 20), description="Tiền tiết kiệm đợt 1"
            )

            self.stdout.write(f"✓ Created 4 saving plans with realistic contributions and goal milestones.")

        self.stdout.write(self.style.SUCCESS("All demo data seeded successfully!"))
