from datetime import date, datetime
from decimal import Decimal
from rest_framework import serializers
from .models import (Transaction, SavingPlan, Wallet, CustomLabel, CategoryBudget,
                     SavingPlanContribution, DebtLoan, DebtPayment)

from django.utils import timezone

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken


class SafeDateField(serializers.DateField):
    def to_representation(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return super().to_representation(value)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['email'] = user.email

        return token


class MyTokenRefreshSerializer(TokenRefreshSerializer):
    refresh = None
    def validate(self, attrs):
        attrs['refresh'] = self.context['request'].COOKIES.get('refresh_token')
        if attrs['refresh']:
            return super().validate(attrs)
        else:
            raise InvalidToken('No valid token found in cookie \'refresh_token\'')


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomLabel
        fields = ('id', 'name', 'color')


class WalletSerializer(serializers.ModelSerializer):
    monthly_earnings = serializers.SerializerMethodField(source='get_monthly_earnings')
    monthly_expenses = serializers.SerializerMethodField(source='get_monthly_expenses')
    labels = LabelSerializer(many=True)

    class Meta:
        model = Wallet
        fields = ('current_amount', 'monthly_earnings', 'monthly_expenses', 'labels')

    @staticmethod
    def get_monthly_earnings(obj):
        return obj.get_monthly_earnings()

    @staticmethod
    def get_monthly_expenses(obj):
        return obj.get_monthly_expenses()


class TransactionSerializer(serializers.ModelSerializer):
    date = SafeDateField(format="%m-%d-%Y", input_formats=['%m-%d-%Y'])
    value = serializers.DecimalField(decimal_places=2, max_digits=15)
    amount = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    label = LabelSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = ('id', 'value', 'date', 'type', 'title', 'label', 'recurrent', 'amount', 'duration', 'imported')

    @staticmethod
    def get_amount(obj):
        if obj.recurrent and hasattr(obj, 'recurrency') and obj.recurrency:
            return obj.recurrency.amount
        return None

    @staticmethod
    def get_duration(obj):
        if obj.recurrent and hasattr(obj, 'recurrency') and obj.recurrency:
            return obj.recurrency.duration
        return None


class SavingPlanContributionSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(decimal_places=2, max_digits=15)
    date = serializers.DateField(format="%Y-%m-%d", input_formats=['%Y-%m-%d', '%m-%d-%Y'])

    class Meta:
        model = SavingPlanContribution
        fields = ('id', 'saving_plan', 'amount', 'date', 'description', 'idempotency_key', 'created_at', 'updated_at')
        read_only_fields = ('id', 'saving_plan', 'created_at', 'updated_at')


class SavingPlanSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(decimal_places=2, max_digits=15)
    target_amount = serializers.DecimalField(source='amount', decimal_places=2, max_digits=15, read_only=True)
    goal_date = serializers.DateField(format="%Y-%m-%d", input_formats=['%Y-%m-%d', '%m-%d-%Y'], required=False, allow_null=True)
    target_date = serializers.DateField(source='goal_date', format="%Y-%m-%d", read_only=True, allow_null=True)
    amount_saved = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    contribution_count = serializers.SerializerMethodField()
    estimated_completion = serializers.SerializerMethodField()

    class Meta:
        model = SavingPlan
        fields = (
            'id', 'title', 'amount', 'target_amount', 'active', 'goal_date', 'target_date',
            'description', 'amount_saved', 'remaining_amount', 'completion_percentage',
            'status', 'contribution_count', 'estimated_completion'
        )

    @staticmethod
    def get_amount_saved(obj):
        return obj.get_amount_saved()

    @staticmethod
    def get_remaining_amount(obj):
        return obj.get_remaining_amount()

    @staticmethod
    def get_completion_percentage(obj):
        return obj.get_completion_percentage()

    @staticmethod
    def get_status(obj):
        return obj.get_status()

    @staticmethod
    def get_contribution_count(obj):
        return obj.contributions.count()

    @staticmethod
    def get_estimated_completion(obj):
        return obj.get_estimated_completion()


class CategoryBudgetSerializer(serializers.ModelSerializer):
    label = LabelSerializer(read_only=True)
    amount = serializers.DecimalField(decimal_places=2, max_digits=15)
    limit = serializers.DecimalField(source='amount', decimal_places=2, max_digits=15, read_only=True)
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_over_budget = serializers.SerializerMethodField()

    class Meta:
        model = CategoryBudget
        fields = (
            'id',
            'label',
            'amount',
            'limit',
            'month',
            'year',
            'spent',
            'remaining',
            'percentage',
            'status',
            'is_over_budget',
            'created_at',
            'updated_at',
        )

    def _get_spent(self, obj):
        expenses_by_label = self.context.get('expenses_by_label')
        if expenses_by_label is not None:
            return expenses_by_label.get(obj.label_id, Decimal('0.00'))
        return obj.get_spent()

    def get_spent(self, obj):
        return f"{self._get_spent(obj):.2f}"

    def get_remaining(self, obj):
        spent = self._get_spent(obj)
        remaining = max(Decimal('0.00'), obj.amount - spent)
        return f"{remaining:.2f}"

    def get_percentage(self, obj):
        if obj.amount <= 0:
            return 0.0
        spent = self._get_spent(obj)
        return round(float(spent / obj.amount) * 100, 2)

    def get_status(self, obj):
        if obj.amount <= 0:
            return "normal"
        spent = self._get_spent(obj)
        pct = (spent / obj.amount) * 100
        if pct > 100:
            return "exceeded"
        elif pct >= 80:
            return "approaching"
        return "normal"

    def get_is_over_budget(self, obj):
        spent = self._get_spent(obj)
        return spent > obj.amount


class DebtPaymentSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(decimal_places=2, max_digits=15)
    date = serializers.DateField(format="%Y-%m-%d", input_formats=['%Y-%m-%d', '%m-%d-%Y'])

    class Meta:
        model = DebtPayment
        fields = (
            'id', 'debt', 'amount', 'date', 'update_wallet', 'note', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'debt', 'created_at', 'updated_at')


class DebtLoanSerializer(serializers.ModelSerializer):
    principal_amount = serializers.DecimalField(decimal_places=2, max_digits=15)
    start_date = serializers.DateField(format="%Y-%m-%d", input_formats=['%Y-%m-%d', '%m-%d-%Y'])
    due_date = serializers.DateField(format="%Y-%m-%d", input_formats=['%Y-%m-%d', '%m-%d-%Y'], required=False, allow_null=True)
    total_paid = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()
    payments = DebtPaymentSerializer(many=True, read_only=True)
    installment_schedule = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = DebtLoan
        fields = (
            'id', 'person_name', 'contact_info', 'type', 'principal_amount',
            'start_date', 'due_date', 'installment_months', 'status', 'description',
            'wallet_applied', 'created_at', 'updated_at',
            'total_paid', 'remaining_amount', 'overdue_days', 'progress_percentage',
            'payments', 'installment_schedule'
        )
        read_only_fields = ('id', 'status', 'wallet_applied', 'created_at', 'updated_at')

    @staticmethod
    def get_total_paid(obj):
        return f"{obj.get_total_paid():.2f}"

    @staticmethod
    def get_remaining_amount(obj):
        return f"{obj.get_remaining_amount():.2f}"

    @staticmethod
    def get_status(obj):
        return obj.get_computed_status()

    @staticmethod
    def get_overdue_days(obj):
        return obj.get_overdue_days()

    @staticmethod
    def get_progress_percentage(obj):
        if obj.principal_amount <= 0:
            return 100.0
        pct = (obj.get_total_paid() / obj.principal_amount) * 100
        return round(float(min(Decimal('100.00'), pct)), 2)

    @staticmethod
    def get_installment_schedule(obj):
        return obj.get_installment_schedule()


