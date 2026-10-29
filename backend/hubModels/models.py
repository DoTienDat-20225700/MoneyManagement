from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import re
from django.core.exceptions import ValidationError
from django.db import models, transaction as db_transaction
from django.db.models import QuerySet, Sum, F
from django.core.mail import send_mail
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from .managers import HubUserManager, TransactionsManager, TransactionsQueryset

from datetime import date, datetime, timedelta
import math
from dateutil.relativedelta import relativedelta
from django.utils import timezone


class HubUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('email address', unique=True)
    first_name = models.CharField('first name', max_length=30, blank=True)
    last_name = models.CharField('last name', max_length=30, blank=True)
    date_joined = models.DateTimeField('date joined', auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = HubUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    @staticmethod
    def create_from_json(data: dict):
        if not isinstance(data, dict):
            raise ValidationError('Dữ liệu tạo tài khoản phải là một đối tượng.')

        email = data.get("email")
        if not email or not isinstance(email, str) or not email.strip():
            raise ValidationError({'email': 'Email là bắt buộc.'})
        email = email.strip()

        from django.core.validators import validate_email
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError({'email': 'Địa chỉ email không hợp lệ.'})

        if HubUser.objects.filter(email__iexact=email).exists():
            raise ValidationError({'email': 'Email này đã được sử dụng.'})

        password = data.get("password")
        if not password or not isinstance(password, str) or not password.strip():
            raise ValidationError({'password': 'Mật khẩu là bắt buộc.'})

        first_name = str(data.get("firstName") or "").strip()
        last_name = str(data.get("lastName") or "").strip()

        user = HubUser.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
        )
        return user

    def get_wallet(self) -> 'Wallet':
        """
        Returns the wallet related to that user.
        """
        return Wallet.objects.get(user_id=self.pk)

    def get_labels(self) -> QuerySet['CustomLabel']:
        """
        Return all CustomLabels related to that user
        """
        return self.get_wallet().get_labels()

    def get_saving_plans(self) -> QuerySet['SavingPlan']:
        """
        Return all SavingPlans related to that user
        """
        return self.get_wallet().get_saving_plans()

    def get_debts(self) -> QuerySet:
        return self.get_wallet().get_debts()


    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """
        Returns the short name for the user.
        """
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)


class Wallet(models.Model):
    user = models.ForeignKey(HubUser, on_delete=models.CASCADE)
    current_amount = models.DecimalField(decimal_places=2, max_digits=15)

    constraints = [
        models.UniqueConstraint(fields=['user'], name='unique wallet per user')
    ]

    def update_balance(self, value):
        """Atomically apply a delta and keep this instance in sync.

        Transaction creation, editing and deletion all use this method.  Taking
        a row lock prevents two requests from calculating a new balance from
        the same stale value.
        """
        try:
            delta = Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError('Wallet balance adjustment must be numeric.')
        if not delta.is_finite():
            raise ValidationError('Wallet balance adjustment must be finite.')

        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)
            new_amount = wallet.current_amount + delta
            if not new_amount.is_finite() or len(new_amount.as_tuple().digits) > 15 \
                    or -new_amount.as_tuple().exponent > 2:
                raise ValidationError('Wallet balance is outside the supported range.')
            wallet.current_amount = new_amount
            wallet.save(update_fields=['current_amount'])
            self.current_amount = wallet.current_amount

    def set_balance(self, value):
        try:
            amount = Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError('Wallet balance must be numeric.')

        if not amount.is_finite():
            raise ValidationError('Wallet balance must be finite.')
        if len(amount.as_tuple().digits) > 15 or -amount.as_tuple().exponent > 2:
            raise ValidationError('Wallet balance supports at most 15 digits and 2 decimal places.')

        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)
            wallet.current_amount = amount
            wallet.save(update_fields=['current_amount'])
            self.current_amount = wallet.current_amount

    def get_current_amount(self):
        return self.current_amount

    def get_transactions(self) -> TransactionsQueryset:
        """
        Return a QuerySet of all non-recurrent Transactions related to a Wallet
        """
        return self.transactions.filter(recurrent=False)

    def get_expenses(self) -> TransactionsQueryset:
        """
        Return a QuerySet of all non-recurrent Transactions related to a Wallet
        """
        return self.get_transactions().expenses()

    def get_monthly_earnings(self):
        """
        Returns the monthly earnings value of a user's Wallet
        """
        today = timezone.localdate()
        return self.transactions.filter(date__year=today.year, date__month=today.month, type="EARNING") \
            .aggregate(Sum('value')).get('value__sum') or 0

    def get_monthly_expenses(self):
        """
        Returns the monthly debt value of a user's Wallet
        """
        today = timezone.localdate()
        return self.transactions.filter(date__year=today.year, date__month=today.month, type="EXPENSE")\
            .aggregate(Sum('value')).get('value__sum') or 0

    def get_saving_plans(self):
        return self.saving_plans.all()

    def get_labels(self) -> QuerySet['CustomLabel']:
        return self.labels.all()

    def get_category_budgets(self, month=None, year=None):
        qs = self.category_budgets.all()
        if year is not None:
            qs = qs.filter(year=year)
        if month is not None:
            qs = qs.filter(month=month)
        return qs

    def get_debts(self):
        return self.debts.all()



class WalletBasedModel(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=False)

    class Meta:
        abstract = True

    def get_wallet(self):
        return self.wallet

    def is_from_wallet(self, wallet):
        if not isinstance(wallet, Wallet):
            raise TypeError("Expected a Wallet instance.")

        if not self.get_wallet() == wallet:
            return False
        return True


class CustomLabel(WalletBasedModel):
    # OVERRIDE
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, null=False, related_name='labels')

    name = models.CharField(max_length=30, blank=False, null=False)
    color = models.CharField(max_length=7, blank=False,
                             null=False)  # HEX FIELD

    def __str__(self):
        return self.name

    @staticmethod
    def create_from_json(data: dict, user_pk: int) -> 'CustomLabel':
        if not isinstance(data, dict):
            raise ValidationError('Label payload must be an object.')
        try:
            user: HubUser = HubUser.objects.get(pk=user_pk)
        except HubUser.DoesNotExist:
            raise PermissionError()

        user_wallet = user.get_wallet()

        if not user_wallet:
            raise PermissionError()

        name = data.get('name')
        color = data.get('color')
        if not isinstance(name, str) or not name.strip():
            raise ValidationError({'name': 'Name is required.'})
        if len(name.strip()) > 30:
            raise ValidationError({'name': 'Name must not exceed 30 characters.'})
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValidationError({'color': 'Color must be a six-digit hex value.'})

        label = CustomLabel(wallet=user_wallet, name=name.strip(), color=color)

        label.save()

        return label


class TransactionRecurrency(models.Model):
    """
    Class that will store the amount of a time a certain transaction
    will be replicated starting from a determined date.
    """
    DURATION_TYPES = [
        ('DAYS', 'days'),
        ('WEEKS', 'weeks'),
        ('MONTHS', 'months'),
        ('YEARS', 'years'),
    ]
    transaction = models.ForeignKey('Transaction', on_delete=models.CASCADE)
    amount = models.IntegerField()
    duration = models.CharField(max_length=6, choices=DURATION_TYPES)
    end_date = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def trigger_async_instantiation(self):
        pass

    def get_amount(self):
        return self.amount

    def get_duration(self):
        return self.duration


class Transaction(WalletBasedModel):
    TRANSACTION_TYPES = [
        ('EXPENSE', 'Expense'),
        ('EARNING', 'Earning'),
    ]

    title = models.CharField(max_length=200, blank=False, null=False)
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, null=False, related_name='transactions')
    value = models.DecimalField(decimal_places=2, max_digits=15)
    date = models.DateField(auto_now=False)
    type = models.CharField(max_length=7, choices=TRANSACTION_TYPES, null=True)
    label = models.ForeignKey(CustomLabel, on_delete=models.SET_NULL, null=True, blank=True)
    imported = models.BooleanField(default=False, null=True, blank=True)
    # Django convention is to avoid setting null=True to CharFields
    update_wallet = models.BooleanField(default=False)
    # Recurrency section
    recurrent = models.BooleanField(default=False)
    recurrency = models.OneToOneField(
        TransactionRecurrency, on_delete=models.CASCADE, null=True, blank=True, related_name='+')
    base_transaction = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True)
    # Manager section
    objects = TransactionsManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('base_transaction', 'date'),
                name='unique_generated_recurrence_occurrence',
            ),
        ]

    @staticmethod
    def _parse_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValidationError({'date': 'A valid transaction date is required.'})

        try:
            # Date-only values are the normal API contract.  ISO datetimes are
            # also accepted because Dayjs serialises request data that way.
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except ValueError:
            raise ValidationError({'date': 'Use an ISO-8601 date or datetime.'})

    @classmethod
    def _parse_value(cls, value):
        if isinstance(value, bool):
            raise ValidationError({'value': 'Value must be a positive number.'})
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({'value': 'Value must be a positive number.'})
        if not amount.is_finite() or amount <= 0:
            raise ValidationError({'value': 'Value must be a positive number.'})
        if len(amount.as_tuple().digits) > 15 or -amount.as_tuple().exponent > 2:
            raise ValidationError({'value': 'Value supports at most 15 digits and 2 decimal places.'})
        return amount

    @classmethod
    def _parse_type(cls, value):
        valid_types = {choice[0] for choice in cls.TRANSACTION_TYPES}
        if value not in valid_types:
            raise ValidationError({'type': 'Type must be EXPENSE or EARNING.'})
        return value

    @staticmethod
    def _parse_boolean(value, field_name):
        if isinstance(value, bool):
            return value
        raise ValidationError({field_name: 'Must be a boolean.'})

    def wallet_effect(self):
        """Return this transaction's signed wallet effect, if any."""
        if not self.update_wallet:
            return Decimal('0')
        return self.value if self.type == 'EARNING' else -self.value

    def save(self, is_first_save=False, **kwargs):
        """Save a new transaction and apply its balance effect exactly once.

        Existing records deliberately do not adjust a wallet here.  Their
        changes must go through ``update_from_json`` so the old effect can be
        reversed before the new one is applied.
        """
        if isinstance(self.date, datetime):
            self.date = self.date.date()
        should_apply_effect = is_first_save and self._state.adding and self.wallet_effect()
        with db_transaction.atomic():
            result = super().save(**kwargs)
            if should_apply_effect:
                self.wallet.update_balance(self.wallet_effect())
            return result

    def delete(self, **kwargs):
        # Query the current row first: a repeated delete on a stale instance
        # must not reverse the balance twice.
        with db_transaction.atomic():
            try:
                current = Transaction.objects.select_related('wallet').get(pk=self.pk)
            except Transaction.DoesNotExist:
                return super().delete(**kwargs)

            effect = current.wallet_effect()
            if effect:
                current.wallet.update_balance(-effect)
            return super().delete(**kwargs)

    @staticmethod
    def create_from_json(data: dict, user_pk: int) -> 'Transaction':
        """
        Creates a transaction from a frontend request
        @params: 
            data : dict
        """
        if not isinstance(data, dict):
            raise ValidationError('Transaction payload must be an object.')

        with db_transaction.atomic():
            try:
                user = HubUser.objects.get(pk=user_pk)
                user_wallet = Wallet.objects.select_for_update().get(user=user)
            except (HubUser.DoesNotExist, Wallet.DoesNotExist):
                raise PermissionError()

            title = data.get('title')
            if not isinstance(title, str) or not title.strip():
                raise ValidationError({'title': 'Title is required.'})
            if len(title.strip()) > 200:
                raise ValidationError({'title': 'Title must not exceed 200 characters.'})

            transaction = Transaction(
                wallet=user_wallet,
                title=title.strip(),
                value=Transaction._parse_value(data.get('value')),
                type=Transaction._parse_type(data.get('type')),
                date=Transaction._parse_date(data.get('date')),
            )

            if data.get('updateWallet') is not None:
                transaction.update_wallet = Transaction._parse_boolean(
                    data.get('updateWallet'), 'updateWallet')

            label_data = data.get('label')
            if label_data is not None:
                label_id = label_data.get('id') if isinstance(label_data, dict) else None
                if not label_id:
                    raise ValidationError({'label': 'Label must include an id.'})
                try:
                    transaction.label = CustomLabel.objects.get(pk=label_id, wallet=user_wallet)
                except CustomLabel.DoesNotExist:
                    raise ValidationError({'label': 'Label does not belong to this wallet.'})

            recurrent = data.get('recurrent', data.get('recurring', False))
            transaction.recurrent = Transaction._parse_boolean(recurrent, 'recurrent')
            if transaction.recurrent:
                raw_amount = data.get('amount')
                duration = data.get('duration')
                try:
                    if isinstance(raw_amount, bool):
                        raise ValueError
                    amount = int(raw_amount)
                    if amount <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ValidationError({'amount': 'Amount must be a positive integer.'})
                valid_durations = {choice[0] for choice in TransactionRecurrency.DURATION_TYPES}
                if duration not in valid_durations:
                    raise ValidationError({'duration': 'Duration is invalid.'})

            transaction.save(is_first_save=True)

            if transaction.recurrent:
                recurrency = TransactionRecurrency.objects.create(
                    transaction=transaction,
                    amount=amount,
                    duration=duration,
                )
                transaction.recurrency = recurrency
                transaction.save()

            return transaction

    @classmethod
    def update_from_json(cls, transaction_pk, user, data):
        """Update an owned transaction while keeping wallet balances correct."""
        if not isinstance(data, dict):
            raise ValidationError('Transaction payload must be an object.')

        with db_transaction.atomic():
            try:
                transaction = cls.objects.select_for_update(of=('self',)).select_related('wallet').get(
                    pk=transaction_pk, wallet__user=user)
            except cls.DoesNotExist:
                raise cls.DoesNotExist()

            original_wallet_id = transaction.wallet_id
            original_effect = transaction.wallet_effect()

            if 'wallet_id' in data or 'wallet' in data:
                wallet_id = data.get('wallet_id', data.get('wallet'))
                if isinstance(wallet_id, dict):
                    wallet_id = wallet_id.get('id')
                try:
                    transaction.wallet = Wallet.objects.get(pk=wallet_id, user=user)
                except (Wallet.DoesNotExist, TypeError, ValueError):
                    raise ValidationError({'wallet_id': 'Wallet does not belong to this user.'})

            if 'title' in data:
                title = data['title']
                if not isinstance(title, str) or not title.strip():
                    raise ValidationError({'title': 'Title is required.'})
                if len(title.strip()) > 200:
                    raise ValidationError({'title': 'Title must not exceed 200 characters.'})
                transaction.title = title.strip()
            if 'value' in data:
                transaction.value = cls._parse_value(data['value'])
            if 'type' in data:
                transaction.type = cls._parse_type(data['type'])
            if 'date' in data:
                transaction.date = cls._parse_date(data['date'])
            if 'updateWallet' in data:
                transaction.update_wallet = cls._parse_boolean(data['updateWallet'], 'updateWallet')

            if 'label' in data or 'label_id' in data:
                label_data = data.get('label', data.get('label_id'))
                label_id = label_data.get('id') if isinstance(label_data, dict) else label_data
                if label_id in (None, ''):
                    transaction.label = None
                else:
                    try:
                        transaction.label = CustomLabel.objects.get(pk=label_id, wallet=transaction.wallet)
                    except (CustomLabel.DoesNotExist, TypeError, ValueError):
                        raise ValidationError({'label': 'Label does not belong to this wallet.'})

            if 'recurrent' in data:
                transaction.recurrent = cls._parse_boolean(data['recurrent'], 'recurrent')

            if transaction.recurrent and ('amount' in data or 'duration' in data):
                raw_amount = data.get('amount')
                duration = data.get('duration')
                if transaction.recurrency:
                    if raw_amount is None:
                        raw_amount = transaction.recurrency.amount
                    if duration is None:
                        duration = transaction.recurrency.duration
                try:
                    if isinstance(raw_amount, bool):
                        raise ValueError
                    amount = int(raw_amount)
                    if amount <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ValidationError({'amount': 'Amount must be a positive integer.'})
                valid_durations = {choice[0] for choice in TransactionRecurrency.DURATION_TYPES}
                if duration not in valid_durations:
                    raise ValidationError({'duration': 'Duration is invalid.'})
                if transaction.recurrency:
                    transaction.recurrency.amount = amount
                    transaction.recurrency.duration = duration
                    transaction.recurrency.save()
                else:
                    recurrency = TransactionRecurrency.objects.create(
                        transaction=transaction,
                        amount=amount,
                        duration=duration,
                        active=True,
                    )
                    transaction.recurrency = recurrency

            # Acquire the affected wallet rows in a stable order before any
            # balance calculation.  This avoids stale read/modify/write
            # updates and reduces deadlock risk if wallets are ever movable.
            wallets = {
                wallet.pk: wallet for wallet in Wallet.objects.select_for_update()
                .filter(pk__in={original_wallet_id, transaction.wallet_id}).order_by('pk')
            }
            if original_effect:
                wallets[original_wallet_id].update_balance(-original_effect)

            transaction.wallet = wallets[transaction.wallet_id]
            transaction.imported = False
            transaction.save()

            new_effect = transaction.wallet_effect()
            if new_effect:
                wallets[transaction.wallet_id].update_balance(new_effect)
            return transaction

    @staticmethod
    def create_from_import(imported_data, optional_data, user):
        """
        Creates a transaction from a frontend request
        @params:
            data : dict
        """
        user_wallet = user.get_wallet()

        if not user_wallet:
            raise PermissionError()

        transaction = Transaction()
        transaction.wallet = user_wallet
        # Imported transactions will always be flagged as imported until they have all the fields completed
        transaction.imported = True

        # Empty fields section
        transaction.title = imported_data.get('title') or ''
        imported_type = optional_data.get('type')
        transaction.type = Transaction._parse_type(imported_type) if imported_type else None
        transaction.update_wallet = bool(optional_data.get('update_wallet'))

        label_id = optional_data.get('label_id')
        if label_id:
            try:
                transaction.label = CustomLabel.objects.get(pk=label_id, wallet=user_wallet)
            except CustomLabel.DoesNotExist:
                pass

        # Invoice dict section
        transaction.value = Transaction._parse_value(imported_data.get("value"))
        transaction.date = Transaction._parse_date(imported_data.get("date"))

        transaction.save(is_first_save=True)
        return transaction

    def is_recurrent(self):
        return self.recurrent

    def get_label(self):
        return self.label


class SavingPlan(WalletBasedModel):
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='saving_plans')
    title = models.CharField(max_length=50)
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    active = models.BooleanField(default=True)
    goal_date = models.DateField(blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, default='')

    def toggle_active(self):
        self.active = not self.active
        self.save(update_fields=['active'])

    @staticmethod
    def _parse_amount(value):
        if isinstance(value, bool):
            raise ValidationError({'amount': 'Amount must be a positive number.'})
        try:
            val = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({'amount': 'Amount must be a positive number.'})
        if not val.is_finite() or val <= 0:
            raise ValidationError({'amount': 'Amount must be a positive number.'})
        if len(val.as_tuple().digits) > 15 or -val.as_tuple().exponent > 2:
            raise ValidationError({'amount': 'Amount supports at most 15 digits and 2 decimal places.'})
        return val

    @staticmethod
    def _parse_date(value):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except ValueError:
            raise ValidationError({'goal_date': 'Use an ISO-8601 date (YYYY-MM-DD).'})

    @classmethod
    def create_from_json(cls, data: dict, user_pk: int) -> 'SavingPlan':
        if not isinstance(data, dict):
            raise ValidationError('Saving plan payload must be an object.')

        try:
            user = HubUser.objects.get(pk=user_pk)
            user_wallet = user.get_wallet()
        except (HubUser.DoesNotExist, Wallet.DoesNotExist):
            raise PermissionError()

        title = data.get('title')
        if not isinstance(title, str) or not title.strip():
            raise ValidationError({'title': 'Title is required.'})
        if len(title.strip()) > 50:
            raise ValidationError({'title': 'Title must not exceed 50 characters.'})

        amount = cls._parse_amount(data.get('amount'))
        goal_date = cls._parse_date(data.get('goal_date', data.get('goalDate')))
        description = data.get('description', '')
        if description and len(str(description).strip()) > 200:
            raise ValidationError({'description': 'Description must not exceed 200 characters.'})

        active = data.get('active', True)
        if not isinstance(active, bool):
            active = True

        plan = cls.objects.create(
            wallet=user_wallet,
            title=title.strip(),
            amount=amount,
            goal_date=goal_date,
            description=str(description).strip() if description else '',
            active=active,
        )
        return plan

    @classmethod
    def update_from_json(cls, plan_pk: int, user: HubUser, data: dict) -> 'SavingPlan':
        if not isinstance(data, dict):
            raise ValidationError('Saving plan payload must be an object.')

        try:
            plan = cls.objects.get(pk=plan_pk, wallet__user=user)
        except cls.DoesNotExist:
            raise cls.DoesNotExist()

        if 'title' in data:
            title = data['title']
            if not isinstance(title, str) or not title.strip():
                raise ValidationError({'title': 'Title is required.'})
            if len(title.strip()) > 50:
                raise ValidationError({'title': 'Title must not exceed 50 characters.'})
            plan.title = title.strip()

        if 'amount' in data:
            plan.amount = cls._parse_amount(data['amount'])

        if 'goal_date' in data or 'goalDate' in data:
            plan.goal_date = cls._parse_date(data.get('goal_date', data.get('goalDate')))

        if 'description' in data:
            description = data['description'] or ''
            if len(str(description).strip()) > 200:
                raise ValidationError({'description': 'Description must not exceed 200 characters.'})
            plan.description = str(description).strip()

        if 'active' in data:
            if not isinstance(data['active'], bool):
                raise ValidationError({'active': 'Active must be a boolean.'})
            plan.active = data['active']

        plan.save()
        return plan

    def get_amount_saved(self) -> Decimal:
        total = self.contributions.aggregate(total=Sum('amount'))['total']
        return total if total is not None else Decimal('0.00')

    def get_remaining_amount(self) -> Decimal:
        saved = self.get_amount_saved()
        target = self.amount or Decimal('0.00')
        rem = target - saved
        return rem if rem > Decimal('0.00') else Decimal('0.00')

    def get_completion_percentage(self) -> float:
        if not self.amount or self.amount <= Decimal('0.00'):
            return 0.0
        saved = self.get_amount_saved()
        pct = float((saved / self.amount) * 100)
        return round(pct, 1)

    def get_status(self) -> str:
        if not self.active:
            return 'closed'
        if self.get_amount_saved() >= self.amount:
            return 'completed'
        return 'active'

    def get_estimated_completion(self) -> dict:
        saved = self.get_amount_saved()
        if saved >= self.amount:
            return {
                'status': 'completed',
                'estimated_date': None,
                'message': 'Mục tiêu đã hoàn thành!',
                'daily_rate': 0.0,
                'days_remaining': 0,
            }
        if not self.active:
            return {
                'status': 'closed',
                'estimated_date': None,
                'message': 'Kế hoạch đang tạm dừng hoặc đã đóng.',
                'daily_rate': 0.0,
                'days_remaining': None,
            }

        contribs = list(self.contributions.order_by('date', 'created_at'))
        if not contribs:
            return {
                'status': 'active',
                'estimated_date': None,
                'message': 'Chưa có lịch sử đóng góp nào để ước tính ngày hoàn thành.',
                'daily_rate': 0.0,
                'days_remaining': None,
            }

        first_date = contribs[0].date
        today = date.today()
        days_span = (today - first_date).days
        total_contributed = sum((c.amount for c in contribs), Decimal('0.00'))

        if days_span <= 0:
            if len(contribs) < 2:
                return {
                    'status': 'active',
                    'estimated_date': None,
                    'message': 'Cần thêm thời gian và các lần đóng góp tiếp theo để dự đoán chính xác.',
                    'daily_rate': 0.0,
                    'days_remaining': None,
                }
            effective_days = Decimal('1.0')
        else:
            effective_days = Decimal(str(days_span))

        daily_rate = total_contributed / effective_days
        if daily_rate <= Decimal('0.00'):
            return {
                'status': 'active',
                'estimated_date': None,
                'message': 'Tốc độ đóng góp không đủ để dự đoán ngày hoàn thành.',
                'daily_rate': 0.0,
                'days_remaining': None,
            }

        remaining = self.get_remaining_amount()
        days_needed = math.ceil(float(remaining / daily_rate))
        estimated_date = today + timedelta(days=days_needed)

        return {
            'status': 'active',
            'estimated_date': estimated_date.isoformat(),
            'message': None,
            'daily_rate': round(float(daily_rate), 2),
            'days_remaining': days_needed,
        }


class SavingPlanContribution(models.Model):
    saving_plan = models.ForeignKey(
        SavingPlan, on_delete=models.CASCADE, related_name='contributions')
    user = models.ForeignKey(
        HubUser, on_delete=models.CASCADE, related_name='saving_contributions')
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=200, blank=True, default='')
    idempotency_key = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'idempotency_key'],
                condition=models.Q(idempotency_key__isnull=False) & ~models.Q(idempotency_key=''),
                name='unique_user_saving_contrib_idempotency'
            )
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.saving_plan.title}: {self.amount} ({self.date})"

    @classmethod
    def create_from_json(cls, plan_pk: int, user: HubUser, data: dict) -> 'SavingPlanContribution':
        if not isinstance(data, dict):
            raise ValidationError('Saving contribution payload must be an object.')

        try:
            plan = SavingPlan.objects.get(pk=plan_pk, wallet__user=user)
        except SavingPlan.DoesNotExist:
            raise SavingPlan.DoesNotExist()

        idempotency_key = data.get('idempotency_key') or data.get('idempotencyKey')
        if idempotency_key:
            idempotency_key = str(idempotency_key).strip()
            existing = cls.objects.filter(user=user, idempotency_key=idempotency_key).first()
            if existing:
                return existing

        amount = SavingPlan._parse_amount(data.get('amount'))
        contrib_date = SavingPlan._parse_date(data.get('date')) or date.today()
        description = data.get('description', '')
        if description and len(str(description).strip()) > 200:
            raise ValidationError({'description': 'Description must not exceed 200 characters.'})

        return cls.objects.create(
            saving_plan=plan,
            user=user,
            amount=amount,
            date=contrib_date,
            description=str(description).strip() if description else '',
            idempotency_key=idempotency_key or None,
        )

    @classmethod
    def update_from_json(cls, contrib_pk: int, user: HubUser, data: dict) -> 'SavingPlanContribution':
        if not isinstance(data, dict):
            raise ValidationError('Saving contribution payload must be an object.')

        try:
            contribution = cls.objects.get(pk=contrib_pk, user=user)
        except cls.DoesNotExist:
            raise cls.DoesNotExist()

        if 'amount' in data:
            contribution.amount = SavingPlan._parse_amount(data['amount'])

        if 'date' in data:
            contrib_date = SavingPlan._parse_date(data['date'])
            if contrib_date:
                contribution.date = contrib_date

        if 'description' in data:
            description = data['description'] or ''
            if len(str(description).strip()) > 200:
                raise ValidationError({'description': 'Description must not exceed 200 characters.'})
            contribution.description = str(description).strip()

        contribution.save()
        return contribution


class CategoryBudget(WalletBasedModel):
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, null=False, related_name='category_budgets')
    label = models.ForeignKey(
        CustomLabel, on_delete=models.CASCADE, null=False, related_name='budgets')
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['wallet', 'label', 'month', 'year'],
                name='unique_wallet_category_monthly_budget',
            ),
        ]
        ordering = ['-year', '-month', 'label__name']

    def __str__(self):
        return f"{self.label.name} Budget ({self.month}/{self.year}): {self.amount}"

    @staticmethod
    def _parse_amount(value):
        if isinstance(value, bool):
            raise ValidationError({'amount': 'Amount must be a positive number.'})
        try:
            val = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({'amount': 'Amount must be a positive number.'})
        if not val.is_finite() or val <= 0:
            raise ValidationError({'amount': 'Amount must be a positive number.'})
        if len(val.as_tuple().digits) > 15 or -val.as_tuple().exponent > 2:
            raise ValidationError({'amount': 'Amount supports at most 15 digits and 2 decimal places.'})
        return val

    @staticmethod
    def _parse_month(value):
        if isinstance(value, bool):
            raise ValidationError({'month': 'Month must be an integer between 1 and 12.'})
        try:
            month = int(value)
        except (TypeError, ValueError):
            raise ValidationError({'month': 'Month must be an integer between 1 and 12.'})
        if month < 1 or month > 12:
            raise ValidationError({'month': 'Month must be between 1 and 12.'})
        return month

    @staticmethod
    def _parse_year(value):
        if isinstance(value, bool):
            raise ValidationError({'year': 'Year must be a valid integer.'})
        try:
            year = int(value)
        except (TypeError, ValueError):
            raise ValidationError({'year': 'Year must be a valid integer.'})
        if year < 2000 or year > 2100:
            raise ValidationError({'year': 'Year must be between 2000 and 2100.'})
        return year

    @classmethod
    def create_from_json(cls, data: dict, user_pk: int) -> 'CategoryBudget':
        if not isinstance(data, dict):
            raise ValidationError('Budget payload must be an object.')

        try:
            user = HubUser.objects.get(pk=user_pk)
            user_wallet = user.get_wallet()
        except (HubUser.DoesNotExist, Wallet.DoesNotExist):
            raise PermissionError()

        label_id = data.get('label_id', data.get('label'))
        if isinstance(label_id, dict):
            label_id = label_id.get('id')
        if not label_id:
            raise ValidationError({'label': 'A category is required for this budget.'})

        try:
            label = CustomLabel.objects.get(pk=label_id, wallet=user_wallet)
        except (CustomLabel.DoesNotExist, TypeError, ValueError):
            raise ValidationError({'label': 'Category does not belong to this wallet.'})

        amount = cls._parse_amount(data.get('amount'))
        month = cls._parse_month(data.get('month', date.today().month))
        year = cls._parse_year(data.get('year', date.today().year))

        if cls.objects.filter(wallet=user_wallet, label=label, month=month, year=year).exists():
            raise ValidationError({'non_field_errors': 'A budget for this category and month already exists.'})

        budget = cls.objects.create(
            wallet=user_wallet,
            label=label,
            amount=amount,
            month=month,
            year=year,
        )
        return budget

    @classmethod
    def update_from_json(cls, budget_pk: int, user: HubUser, data: dict) -> 'CategoryBudget':
        if not isinstance(data, dict):
            raise ValidationError('Budget payload must be an object.')

        try:
            budget = cls.objects.get(pk=budget_pk, wallet__user=user)
        except cls.DoesNotExist:
            raise cls.DoesNotExist()

        if 'label_id' in data or 'label' in data:
            label_id = data.get('label_id', data.get('label'))
            if isinstance(label_id, dict):
                label_id = label_id.get('id')
            try:
                budget.label = CustomLabel.objects.get(pk=label_id, wallet=budget.wallet)
            except (CustomLabel.DoesNotExist, TypeError, ValueError):
                raise ValidationError({'label': 'Category does not belong to this wallet.'})

        if 'amount' in data:
            budget.amount = cls._parse_amount(data['amount'])

        if 'month' in data:
            budget.month = cls._parse_month(data['month'])

        if 'year' in data:
            budget.year = cls._parse_year(data['year'])

        duplicate_qs = cls.objects.filter(
            wallet=budget.wallet,
            label=budget.label,
            month=budget.month,
            year=budget.year
        ).exclude(pk=budget.pk)
        if duplicate_qs.exists():
            raise ValidationError({'non_field_errors': 'A budget for this category and month already exists.'})

        budget.save()
        return budget

    def get_spent(self) -> Decimal:
        spent = Transaction.objects.filter(
            wallet=self.wallet,
            label=self.label,
            type='EXPENSE',
            date__year=self.year,
            date__month=self.month,
        ).aggregate(total=Sum('value'))['total']
        return spent or Decimal('0.00')

    def get_remaining(self) -> Decimal:
        spent = self.get_spent()
        return max(Decimal('0.00'), self.amount - spent)

    def get_percentage(self) -> float:
        if self.amount <= 0:
            return 0.0
        return round(float(self.get_spent() / self.amount) * 100, 2)

    def is_over_budget(self) -> bool:
        return self.get_spent() > self.amount


def calculate_installment_schedule_data(
    principal_amount: Decimal,
    installment_months: int,
    start_date: date,
    total_paid: Decimal,
) -> list:
    if not installment_months or installment_months <= 0:
        return []

    # 1. Determine exact installment amounts so the sum equals principal_amount exactly
    amounts = []
    if installment_months == 1:
        amounts.append(principal_amount)
    else:
        base_amount = (principal_amount / Decimal(installment_months)).quantize(Decimal('1'), rounding=ROUND_FLOOR).quantize(Decimal('0.01'))
        sum_first = Decimal('0.00')
        for _ in range(1, installment_months):
            amounts.append(base_amount)
            sum_first += base_amount
        last_amount = principal_amount - sum_first
        amounts.append(last_amount)

    # 2. Sequentially allocate paid_amount to each installment period
    remaining_paid = total_paid
    schedule = []
    for i, amount in enumerate(amounts, start=1):
        due = start_date + relativedelta(months=i)
        paid_this_period = min(amount, max(Decimal('0.00'), remaining_paid))
        remaining_paid = max(Decimal('0.00'), remaining_paid - paid_this_period)
        is_paid = paid_this_period >= amount
        schedule.append({
            'installment_no': i,
            'due_date': due.isoformat(),
            'amount': f"{amount:.2f}",
            'paid_amount': f"{paid_this_period:.2f}",
            'is_paid': is_paid,
        })
    return schedule


class DebtLoan(WalletBasedModel):
    DEBT_TYPES = (
        ('DEBT_BORROWED', 'Debt Borrowed'),
        ('LOAN_GIVEN', 'Loan Given'),
        ('INSTALLMENT', 'Installment'),
    )

    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('FULLY_PAID', 'Fully Paid'),
        ('OVERDUE', 'Overdue'),
        ('CLOSED', 'Closed'),
    )

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name='debts'
    )
    person_name = models.CharField(max_length=100)
    contact_info = models.CharField(max_length=150, blank=True, default='')
    type = models.CharField(max_length=20, choices=DEBT_TYPES)
    principal_amount = models.DecimalField(decimal_places=2, max_digits=15)
    start_date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    installment_months = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, default='ACTIVE', choices=STATUS_CHOICES)
    description = models.TextField(blank=True, default='')
    wallet_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.person_name} ({self.type}): {self.principal_amount}"

    def get_total_paid(self) -> Decimal:
        if not self.pk:
            return Decimal('0.00')
        total = self.payments.aggregate(t=Sum('amount'))['t']
        return total or Decimal('0.00')

    def get_remaining_amount(self) -> Decimal:
        paid = self.get_total_paid()
        remaining = self.principal_amount - paid
        return max(Decimal('0.00'), remaining)

    def get_computed_status(self) -> str:
        paid = self.get_total_paid()
        remaining = self.principal_amount - paid
        if remaining <= Decimal('0.00'):
            return 'FULLY_PAID'
        today = date.today()
        if self.due_date and today > self.due_date and remaining > Decimal('0.00'):
            return 'OVERDUE'
        if paid > Decimal('0.00'):
            return 'PARTIALLY_PAID'
        if self.status == 'CLOSED':
            return 'CLOSED'
        return 'ACTIVE'

    def get_overdue_days(self) -> int:
        today = date.today()
        remaining = self.get_remaining_amount()
        if self.due_date and today > self.due_date and remaining > Decimal('0.00'):
            return (today - self.due_date).days
        return 0

    def get_installment_schedule(self) -> list:
        if self.type != 'INSTALLMENT' or not self.installment_months or self.installment_months <= 0:
            return []
        return calculate_installment_schedule_data(
            self.principal_amount,
            self.installment_months,
            self.start_date,
            self.get_total_paid(),
        )

    @staticmethod
    def _parse_amount(value, field_name='principal_amount'):
        if isinstance(value, bool):
            raise ValidationError({field_name: 'Số tiền phải là số dương hợp lệ.'})
        try:
            val = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError({field_name: 'Số tiền phải là số hợp lệ.'})
        if not val.is_finite() or val <= 0:
            raise ValidationError({field_name: 'Số tiền phải lớn hơn 0.'})
        if len(val.as_tuple().digits) > 15 or -val.as_tuple().exponent > 2:
            raise ValidationError({field_name: 'Số tiền hỗ trợ tối đa 15 chữ số và 2 chữ số thập phân.'})
        return val

    @staticmethod
    def _parse_date(value, field_name='date'):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except ValueError:
            try:
                return datetime.strptime(value.strip(), '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError({field_name: 'Định dạng ngày không hợp lệ (sử dụng YYYY-MM-DD).'})

    @staticmethod
    def _parse_boolean(value, field_name='update_wallet'):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes'):
                return True
            if value.lower() in ('false', '0', 'no'):
                return False
        raise ValidationError({field_name: 'Giá trị phải là boolean.'})

    @classmethod
    def create_from_json(cls, data: dict, user_pk: int) -> 'DebtLoan':
        if not isinstance(data, dict):
            raise ValidationError('Dữ liệu yêu cầu phải là object.')

        with db_transaction.atomic():
            try:
                user = HubUser.objects.get(pk=user_pk)
                user_wallet = Wallet.objects.select_for_update().get(user=user)
            except (HubUser.DoesNotExist, Wallet.DoesNotExist):
                raise PermissionError('Không tìm thấy ví của người dùng.')

            person_name = data.get('person_name', data.get('personName'))
            if not person_name or not str(person_name).strip():
                raise ValidationError({'person_name': 'Tên người liên quan là bắt buộc.'})
            person_name = str(person_name).strip()
            if len(person_name) > 100:
                raise ValidationError({'person_name': 'Tên không được vượt quá 100 ký tự.'})

            debt_type = data.get('type')
            valid_types = {t[0] for t in cls.DEBT_TYPES}
            if debt_type not in valid_types:
                raise ValidationError({'type': f"Loại hợp đồng phải là một trong các giá trị: {', '.join(valid_types)}."})

            raw_principal = data.get('principal_amount', data.get('principalAmount'))
            principal_amount = cls._parse_amount(raw_principal, 'principal_amount')

            start_date = cls._parse_date(data.get('start_date', data.get('startDate')), 'start_date') or date.today()
            due_date = cls._parse_date(data.get('due_date', data.get('dueDate')), 'due_date')

            installment_months = data.get('installment_months', data.get('installmentMonths'))
            if debt_type == 'INSTALLMENT':
                if not installment_months:
                    raise ValidationError({'installment_months': 'Mua trả góp bắt buộc phải có số tháng trả góp.'})
                try:
                    installment_months = int(installment_months)
                    if installment_months <= 0 or installment_months > 120:
                        raise ValueError()
                except (ValueError, TypeError):
                    raise ValidationError({'installment_months': 'Số tháng trả góp phải từ 1 đến 120 tháng.'})
                if not due_date:
                    due_date = start_date + relativedelta(months=installment_months)
            else:
                if installment_months is not None:
                    try:
                        installment_months = int(installment_months)
                    except (ValueError, TypeError):
                        installment_months = None

            if due_date and start_date and due_date < start_date:
                raise ValidationError({'due_date': 'Ngày đến hạn không thể trước ngày bắt đầu.'})

            contact_info = data.get('contact_info', data.get('contactInfo', ''))
            description = data.get('description', '')

            raw_update_wallet = data.get('update_wallet', data.get('updateWallet', False))
            update_wallet = cls._parse_boolean(raw_update_wallet, 'update_wallet')

            # Wallet adjustments when creating contract
            wallet_applied = False
            if update_wallet:
                if debt_type == 'LOAN_GIVEN':
                    # Cho vay: tiền rời khỏi ví -> trừ ví
                    user_wallet.update_balance(-principal_amount)
                    wallet_applied = True
                elif debt_type == 'DEBT_BORROWED':
                    # Đi vay: nhận được tiền -> cộng vào ví
                    user_wallet.update_balance(principal_amount)
                    wallet_applied = True
                # INSTALLMENT: Không tác động ví lúc tạo (wallet_applied luôn False)

            debt = cls(
                wallet=user_wallet,
                person_name=person_name,
                contact_info=str(contact_info).strip() if contact_info else '',
                type=debt_type,
                principal_amount=principal_amount,
                start_date=start_date,
                due_date=due_date,
                installment_months=installment_months,
                status='ACTIVE',
                description=str(description).strip() if description else '',
                wallet_applied=wallet_applied,
            )
            debt.save()
            computed_status = debt.get_computed_status()
            if computed_status != 'ACTIVE':
                debt.status = computed_status
                debt.save(update_fields=['status'])
            return debt

    @classmethod
    def update_from_json(cls, debt_pk: int, user: HubUser, data: dict) -> 'DebtLoan':
        if not isinstance(data, dict):
            raise ValidationError('Dữ liệu yêu cầu phải là object.')

        with db_transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(user=user)
                debt = cls.objects.select_for_update().get(pk=debt_pk, wallet=wallet)
            except cls.DoesNotExist:
                raise cls.DoesNotExist('Không tìm thấy hợp đồng nợ.')
            except Wallet.DoesNotExist:
                raise PermissionError('Không tìm thấy ví của người dùng.')

            # Check immutability of type and wallet
            cannot_change = debt.payments.exists() or debt.wallet_applied
            if 'type' in data and data['type'] != debt.type:
                if cannot_change:
                    raise ValidationError({'type': 'Không thể thay đổi loại hợp đồng khi đã có thanh toán hoặc đã cập nhật vào ví.'})
                valid_types = {t[0] for t in cls.DEBT_TYPES}
                if data['type'] not in valid_types:
                    raise ValidationError({'type': f"Loại hợp đồng phải là một trong các giá trị: {', '.join(valid_types)}."})
                debt.type = data['type']

            if 'wallet' in data or 'wallet_id' in data:
                new_wallet_id = data.get('wallet_id', data.get('wallet'))
                if str(new_wallet_id) != str(debt.wallet_id):
                    raise ValidationError({'wallet': 'Không thể thay đổi ví của hợp đồng.'})

            if 'person_name' in data or 'personName' in data:
                pname = data.get('person_name', data.get('personName'))
                if not pname or not str(pname).strip():
                    raise ValidationError({'person_name': 'Tên người liên quan không được để trống.'})
                debt.person_name = str(pname).strip()

            if 'contact_info' in data or 'contactInfo' in data:
                debt.contact_info = str(data.get('contact_info', data.get('contactInfo', ''))).strip()

            if 'description' in data:
                debt.description = str(data.get('description', '')).strip()

            if 'due_date' in data or 'dueDate' in data:
                new_due = cls._parse_date(data.get('due_date', data.get('dueDate')), 'due_date')
                if new_due and debt.start_date and new_due < debt.start_date:
                    raise ValidationError({'due_date': 'Ngày đến hạn không thể trước ngày bắt đầu.'})
                debt.due_date = new_due

            if 'principal_amount' in data or 'principalAmount' in data:
                new_principal = cls._parse_amount(data.get('principal_amount', data.get('principalAmount')), 'principal_amount')
                total_paid = debt.get_total_paid()
                if new_principal < total_paid:
                    raise ValidationError({'principal_amount': f'Số tiền gốc ({new_principal}) không được nhỏ hơn tổng tiền đã thanh toán ({total_paid}).'})

                # If wallet_applied was True, adjust the wallet for the principal delta
                if debt.wallet_applied:
                    diff = new_principal - debt.principal_amount
                    if diff != Decimal('0.00'):
                        if debt.type == 'LOAN_GIVEN':
                            wallet.update_balance(-diff)
                        elif debt.type == 'DEBT_BORROWED':
                            wallet.update_balance(diff)
                debt.principal_amount = new_principal

            debt.status = debt.get_computed_status()
            debt.save()
            return debt

    def delete(self, **kwargs):
        wallet_id = self.wallet_id
        with db_transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
            except Wallet.DoesNotExist:
                return super().delete(**kwargs)

            try:
                debt = DebtLoan.objects.select_for_update().get(pk=self.pk)
            except DebtLoan.DoesNotExist:
                raise DebtLoan.DoesNotExist('Hợp đồng nợ không tồn tại hoặc đã bị xóa bởi luồng khác.')

            if debt.wallet_id != wallet.pk:
                raise ValidationError('Ví của hợp đồng nợ đã bị thay đổi, không thể thực hiện thao tác xóa.')

            # 1. Reverse all payments made with update_wallet
            for payment in debt.payments.filter(update_wallet=True):
                if debt.type == 'LOAN_GIVEN':
                    wallet.update_balance(-payment.amount)
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    wallet.update_balance(payment.amount)

            # 2. Reverse initial contract effect ONLY IF wallet_applied = True
            if debt.wallet_applied:
                if debt.type == 'LOAN_GIVEN':
                    wallet.update_balance(debt.principal_amount)
                elif debt.type == 'DEBT_BORROWED':
                    wallet.update_balance(-debt.principal_amount)

            return super(DebtLoan, debt).delete(**kwargs)


class DebtPayment(models.Model):
    debt = models.ForeignKey(
        DebtLoan, on_delete=models.CASCADE, related_name='payments'
    )
    amount = models.DecimalField(decimal_places=2, max_digits=15)
    date = models.DateField(default=timezone.now)
    update_wallet = models.BooleanField(default=False)
    note = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Payment for {self.debt.person_name}: {self.amount} on {self.date}"

    @classmethod
    def create_from_json(cls, debt_pk: int, user: HubUser, data: dict) -> 'DebtPayment':
        if not isinstance(data, dict):
            raise ValidationError('Dữ liệu yêu cầu phải là object.')

        with db_transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(user=user)
                debt = DebtLoan.objects.select_for_update().get(pk=debt_pk, wallet=wallet)
            except DebtLoan.DoesNotExist:
                raise DebtLoan.DoesNotExist('Không tìm thấy hợp đồng nợ.')
            except Wallet.DoesNotExist:
                raise PermissionError('Không tìm thấy ví của người dùng.')

            raw_amount = data.get('amount')
            amount = DebtLoan._parse_amount(raw_amount, 'amount')

            # Calculate remaining amount AFTER locking debt
            remaining = debt.get_remaining_amount()
            if amount > remaining:
                raise ValidationError({'amount': f'Số tiền thanh toán ({amount}) vượt quá dư nợ còn lại ({remaining}).'})

            pay_date = DebtLoan._parse_date(data.get('date'), 'date') or date.today()
            raw_update_wallet = data.get('update_wallet', data.get('updateWallet', False))
            update_wallet = DebtLoan._parse_boolean(raw_update_wallet, 'update_wallet')
            note = str(data.get('note', '')).strip()

            # Wallet effect for payment:
            # LOAN_GIVEN: Thu hồi tiền cho vay -> ví tăng (+)
            # DEBT_BORROWED / INSTALLMENT: Trả nợ / trả góp -> ví giảm (-)
            if update_wallet:
                if debt.type == 'LOAN_GIVEN':
                    wallet.update_balance(amount)
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    wallet.update_balance(-amount)

            payment = cls.objects.create(
                debt=debt,
                amount=amount,
                date=pay_date,
                update_wallet=update_wallet,
                note=note,
            )

            debt.status = debt.get_computed_status()
            debt.save(update_fields=['status'])
            return payment

    @classmethod
    def update_from_json(cls, payment_pk: int, user: HubUser, data: dict) -> 'DebtPayment':
        if not isinstance(data, dict):
            raise ValidationError('Dữ liệu yêu cầu phải là object.')

        with db_transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(user=user)
                debt = DebtLoan.objects.select_for_update(of=('self',)).get(payments__id=payment_pk, wallet=wallet)
                payment = cls.objects.select_for_update().get(pk=payment_pk, debt=debt)
            except (cls.DoesNotExist, DebtLoan.DoesNotExist):
                raise cls.DoesNotExist('Không tìm thấy khoản thanh toán.')
            except Wallet.DoesNotExist:
                raise PermissionError('Không tìm thấy ví của người dùng.')

            other_sum = debt.payments.exclude(pk=payment.pk).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
            max_allowed = debt.principal_amount - other_sum

            if 'amount' in data:
                new_amount = DebtLoan._parse_amount(data['amount'], 'amount')
                if new_amount > max_allowed:
                    raise ValidationError({'amount': f'Số tiền thanh toán ({new_amount}) vượt quá dư nợ tối đa có thể trả ({max_allowed}).'})
            else:
                new_amount = payment.amount

            if 'update_wallet' in data or 'updateWallet' in data:
                new_update_wallet = DebtLoan._parse_boolean(
                    data.get('update_wallet', data.get('updateWallet')), 'update_wallet'
                )
            else:
                new_update_wallet = payment.update_wallet

            # Balance recalculation:
            # 1. Reverse old effect
            old_delta = Decimal('0.00')
            if payment.update_wallet:
                if debt.type == 'LOAN_GIVEN':
                    old_delta = payment.amount
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    old_delta = -payment.amount

            # 2. Compute new effect
            new_delta = Decimal('0.00')
            if new_update_wallet:
                if debt.type == 'LOAN_GIVEN':
                    new_delta = new_amount
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    new_delta = -new_amount

            wallet_diff = new_delta - old_delta
            if wallet_diff != Decimal('0.00'):
                wallet.update_balance(wallet_diff)

            payment.amount = new_amount
            payment.update_wallet = new_update_wallet

            if 'date' in data:
                payment.date = DebtLoan._parse_date(data['date'], 'date') or payment.date

            if 'note' in data:
                payment.note = str(data.get('note', '')).strip()

            payment.save()
            debt.status = debt.get_computed_status()
            debt.save(update_fields=['status'])
            return payment

    @classmethod
    def delete_payment(cls, payment_pk: int, user: HubUser) -> None:
        with db_transaction.atomic():
            try:
                wallet = Wallet.objects.select_for_update().get(user=user)
                debt = DebtLoan.objects.select_for_update(of=('self',)).get(payments__id=payment_pk, wallet=wallet)
                payment = cls.objects.select_for_update().get(pk=payment_pk, debt=debt)
            except (cls.DoesNotExist, DebtLoan.DoesNotExist):
                raise cls.DoesNotExist('Không tìm thấy khoản thanh toán.')
            except Wallet.DoesNotExist:
                raise PermissionError('Không tìm thấy ví của người dùng.')

            if payment.update_wallet:
                if debt.type == 'LOAN_GIVEN':
                    wallet.update_balance(-payment.amount)
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    wallet.update_balance(payment.amount)

            payment.delete()
            debt.status = debt.get_computed_status()
            debt.save(update_fields=['status'])


