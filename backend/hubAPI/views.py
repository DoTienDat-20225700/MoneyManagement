import os
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.db.models import QuerySet, Sum, Q
from .utils import custom_server_error_response, custom_success_response, custom_user_error_response
from hubModels.serializers import MyTokenObtainPairSerializer, MyTokenRefreshSerializer
from hubModels.models import HubUser, Transaction, CustomLabel, SavingPlan, CategoryBudget
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser
from hubModels.serializers import SavingPlanSerializer, WalletSerializer, TransactionSerializer, CategoryBudgetSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from datetime import date
from datetime import timedelta
from hubModels.models import CustomLabel
from hubModels.serializers import LabelSerializer
from hubModels.importer import InvoiceImporter, PDFInvoiceImporter, InvoiceProcessingException
from django.conf import settings
from django.db import transaction as db_transaction
from django.db.models.functions import TruncDate


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get('refresh'):
            response.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=response.data['refresh'],
                # domain=settings.SIMPLE_JWT["AUTH_COOKIE_DOMAIN"],
                # path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                expires=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )
            del response.data['refresh']
        return super().finalize_response(request, response, *args, **kwargs)


class MyTokenRefreshView(TokenRefreshView):
    serializer_class = MyTokenRefreshSerializer

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=403)

        try:
            token = RefreshToken(refresh_token)
            access_token = str(token.access_token)
            return Response({'access_token': access_token, 'refresh_token': refresh_token})
        except Exception:
            return Response({'error': 'Invalid refresh token'}, status=403)

    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get('refresh'):
            response.set_cookie(
                key=settings.SIMPLE_JWT["AUTH_COOKIE"],
                value=response.data['refresh'],
                # domain=settings.SIMPLE_JWT["AUTH_COOKIE_DOMAIN"],
                # path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
                expires=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
                secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
                httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
                samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
            )
            del response.data['refresh']
        return super().finalize_response(request, response, *args, **kwargs)


class WalletAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = WalletSerializer

    def get(self, request):
        user: HubUser = request.user

        wallet = user.get_wallet()
        wallet_serialized = WalletSerializer(wallet)

        return Response(wallet_serialized.data)

    def put(self, request):
        user: HubUser = request.user
        wallet = user.get_wallet()

        try:
            if isinstance(request.data, bool):
                raise InvalidOperation
            value = Decimal(str(request.data))
            if not value.is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            return custom_user_error_response("Entered value needs to be a number. Please try again.", 422)

        try:
            wallet.set_balance(value)
        except ValidationError:
            return custom_user_error_response("Entered value is outside the supported range.", 422)

        return custom_success_response("Wallet's balance successfully updated!")


class TransactionAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TransactionSerializer

    def post(self, request):
        user: HubUser = request.user

        data = request.data
        try:
            Transaction.create_from_json(data, user_pk=user.pk)
        except ValidationError as error:
            return custom_user_error_response(error.message if hasattr(error, 'message') else str(error), 400)
        except PermissionError:
            return custom_user_error_response('Wallet was not found.', 404)

        # TODO: Change response to message string
        return custom_success_response("Transaction created with success!")

    def delete(self, request, transaction_pk=None):
        user: HubUser = request.user

        if not transaction_pk:
            return custom_user_error_response("No transaction id was given. Please try again.", 400)

        with db_transaction.atomic():
            try:
                transaction = Transaction.objects.select_for_update().get(
                    pk=transaction_pk, wallet__user=user)
            except Transaction.DoesNotExist:
                return custom_user_error_response("Không tìm thấy giao dịch.", 404)
            transaction.delete()

        return custom_success_response("Transaction deleted with success!")

    def put(self, request, transaction_pk=None):
        user: HubUser = request.user
        pk = transaction_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("No transaction id was given. Please try again.", 400)

        try:
            Transaction.update_from_json(pk, user, request.data)
        except Transaction.DoesNotExist:
            return custom_user_error_response("Không tìm thấy giao dịch.", 404)
        except ValidationError as error:
            return custom_user_error_response(error.message if hasattr(error, 'message') else str(error), 400)

        return custom_success_response("Cập nhật giao dịch thành công!")


class LabelAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LabelSerializer

    def get(self, request):
        user: HubUser = request.user

        labels = user.get_labels()
        serializer = self.serializer_class(labels, many=True)

        return Response(serializer.data)

    def post(self, request):
        user: HubUser = request.user

        data = request.data
        try:
            CustomLabel.create_from_json(data, user_pk=user.pk)
        except (PermissionError, ValueError, ValidationError):
            return custom_user_error_response("Thông tin nhãn không hợp lệ.", 400)

        return custom_success_response("Label created with success!")

    def delete(self, request, label_pk=None):
        user: HubUser = request.user

        if not label_pk:
            return custom_user_error_response("No label id was given. Please try again.", 400)

        try:
            label = CustomLabel.objects.get(pk=label_pk, wallet__user=user)
        except CustomLabel.DoesNotExist:
            return custom_user_error_response("Không tìm thấy nhãn.", 404)

        label.delete()

        return custom_success_response("Label deleted with success!")


class ImportInvoicesAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user: HubUser = request.user

        files_list = request.FILES.getlist('files[]')

        institution = request.query_params.get('institution')
        update_wallet = request.query_params.get('updateWallet') in ['1', 'true', 'True', True]
        transaction_type = request.query_params.get('type', None)
        label_id = request.query_params.get('label', None)

        if update_wallet and not transaction_type:
            # Update wallet has no effect if transaction type is None
            update_wallet = False

        os.makedirs('hubAPI/imported_files', exist_ok=True)

        for uploaded_file in files_list:
            _, ext = os.path.splitext(uploaded_file.name)
            if not ext:
                ext = '.pdf'
            ext = ext.lower()
            file_path = f'hubAPI/imported_files/buffer_{user.pk}{ext}'

            try:
                with open(file_path, 'wb') as file:
                    for chunk in uploaded_file.chunks():
                        file.write(chunk)

                optional_data = {
                    'update_wallet': update_wallet,
                    'type': transaction_type,
                    'label_id': label_id,
                }

                try:
                    invoice_dict = InvoiceImporter(file_path, institution).process_file()
                except Exception as e:
                    return custom_user_error_response(InvoiceProcessingException.message)

                if not invoice_dict.get('value') and not invoice_dict.get('date'):
                    return custom_user_error_response(InvoiceProcessingException.message)

                try:
                    Transaction.create_from_import(imported_data=invoice_dict, optional_data=optional_data, user=user)
                except Exception as e:
                    return custom_user_error_response('Có lỗi xảy ra khi lưu giao dịch từ hoá đơn. Vui lòng thử lại.')
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return custom_success_response('Đã nhập hoá đơn thành công! Vui lòng cập nhật các thông tin còn thiếu.')


@api_view(['GET'])
def get_routes(request):
    routes = [
        '/api/token',
        '/api/token/refresh',
        '/api/register',
        '/api/wallet',
        '/api/savingplans',
        '/api/transactions',
        '/api/transaction',
        '/api/budgets',
        '/api/budget',
        '/api/budgets/summary',
    ]

    return Response(routes)


@api_view(['POST'])
def create_user(request):
    data = request.data
    try:
        user = HubUser.create_from_json(data)
        return custom_success_response("Tạo tài khoản thành công!")
    except Exception as e:
        return custom_user_error_response("Email này đã được sử dụng hoặc thông tin không hợp lệ.")


class SavingPlanAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SavingPlanSerializer

    def get(self, request, saving_plan_pk=None):
        user: HubUser = request.user
        if saving_plan_pk:
            try:
                plan = SavingPlan.objects.get(pk=saving_plan_pk, wallet__user=user)
                return Response(self.serializer_class(plan).data)
            except SavingPlan.DoesNotExist:
                return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        plans = user.get_saving_plans()
        return Response(self.serializer_class(plans, many=True).data)

    def post(self, request):
        user: HubUser = request.user
        try:
            plan = SavingPlan.create_from_json(request.data, user_pk=user.pk)
            return Response(self.serializer_class(plan).data, status=201)
        except ValidationError as error:
            return custom_user_error_response(error.message if hasattr(error, 'message') else str(error), 400)
        except PermissionError:
            return custom_user_error_response('Wallet was not found.', 404)

    def put(self, request, saving_plan_pk=None):
        user: HubUser = request.user
        pk = saving_plan_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("No saving plan id was given. Please try again.", 400)

        try:
            plan = SavingPlan.update_from_json(pk, user, request.data)
            return Response(self.serializer_class(plan).data, status=200)
        except SavingPlan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)
        except ValidationError as error:
            return custom_user_error_response(error.message if hasattr(error, 'message') else str(error), 400)

    def patch(self, request, saving_plan_pk=None):
        user: HubUser = request.user
        pk = saving_plan_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("No saving plan id was given. Please try again.", 400)

        try:
            plan = SavingPlan.objects.get(pk=pk, wallet__user=user)
        except SavingPlan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        if 'active' in request.data:
            if not isinstance(request.data['active'], bool):
                return custom_user_error_response("Active must be a boolean.", 400)
            plan.active = request.data['active']
            plan.save(update_fields=['active'])
        else:
            plan.toggle_active()

        return Response(self.serializer_class(plan).data, status=200)

    def delete(self, request, saving_plan_pk=None):
        user: HubUser = request.user
        if not saving_plan_pk:
            return custom_user_error_response("No saving plan id was given. Please try again.", 400)

        try:
            plan = SavingPlan.objects.get(pk=saving_plan_pk, wallet__user=user)
        except SavingPlan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        plan.delete()
        return custom_success_response("Kế hoạch tiết kiệm đã được xoá thành công!")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_saving_plans(request):
    user: HubUser = request.user

    saving_plans = user.get_wallet().get_saving_plans()
    saving_plans_serialized = SavingPlanSerializer(saving_plans, many=True)

    return Response(saving_plans_serialized.data)


class BudgetAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CategoryBudgetSerializer

    def get(self, request, budget_pk=None):
        user: HubUser = request.user
        wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        if budget_pk:
            try:
                budget = wallet.category_budgets.select_related('label').get(pk=budget_pk)
                serializer = self.serializer_class(budget)
                return Response(serializer.data)
            except CategoryBudget.DoesNotExist:
                return custom_user_error_response("Không tìm thấy ngân sách.", 404)

        month_param = request.query_params.get('month')
        year_param = request.query_params.get('year')

        today = date.today()
        try:
            month = int(month_param) if month_param else today.month
            year = int(year_param) if year_param else today.year
        except (TypeError, ValueError):
            return custom_user_error_response("Month and year must be valid integers.", 400)

        if month < 1 or month > 12:
            return custom_user_error_response("Month must be between 1 and 12.", 400)
        if year < 2000 or year > 2100:
            return custom_user_error_response("Year must be between 2000 and 2100.", 400)

        budgets = wallet.category_budgets.filter(
            year=year, month=month
        ).select_related('label').order_by('label__name')

        # Single aggregated query to compute actual expense spending by label for this month
        # Excludes earnings, transfers, and transactions belonging to other users.
        expenses_by_label = dict(
            Transaction.objects.filter(
                wallet=wallet,
                type='EXPENSE',
                date__year=year,
                date__month=month,
                label__isnull=False,
            ).values('label_id').annotate(total=Sum('value')).values_list('label_id', 'total')
        )

        serializer = self.serializer_class(
            budgets,
            many=True,
            context={'expenses_by_label': expenses_by_label}
        )
        return Response(serializer.data)

    def post(self, request):
        user: HubUser = request.user
        try:
            budget = CategoryBudget.create_from_json(request.data, user_pk=user.pk)
            serializer = self.serializer_class(budget)
            return Response(serializer.data, status=201)
        except ValidationError as error:
            msg = error.message if hasattr(error, 'message') else str(error)
            if hasattr(error, 'message_dict'):
                for k, v in error.message_dict.items():
                    msg = v[0] if isinstance(v, list) and v else str(v)
                    break
            return custom_user_error_response(msg, 400)
        except PermissionError:
            return custom_user_error_response("Wallet was not found.", 404)

    def put(self, request, budget_pk=None):
        user: HubUser = request.user
        pk = budget_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("No budget id was given. Please try again.", 400)

        try:
            budget = CategoryBudget.update_from_json(pk, user, request.data)
            serializer = self.serializer_class(budget)
            return Response(serializer.data, status=200)
        except CategoryBudget.DoesNotExist:
            return custom_user_error_response("Không tìm thấy ngân sách.", 404)
        except ValidationError as error:
            msg = error.message if hasattr(error, 'message') else str(error)
            if hasattr(error, 'message_dict'):
                for k, v in error.message_dict.items():
                    msg = v[0] if isinstance(v, list) and v else str(v)
                    break
            return custom_user_error_response(msg, 400)

    def delete(self, request, budget_pk=None):
        user: HubUser = request.user
        pk = budget_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("No budget id was given. Please try again.", 400)

        try:
            budget = CategoryBudget.objects.get(pk=pk, wallet__user=user)
        except CategoryBudget.DoesNotExist:
            return custom_user_error_response("Không tìm thấy ngân sách.", 404)

        budget.delete()
        return custom_success_response("Ngân sách đã được xoá thành công!")


class BudgetSummaryAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        month_param = request.query_params.get('month')
        year_param = request.query_params.get('year')

        today = date.today()
        try:
            month = int(month_param) if month_param else today.month
            year = int(year_param) if year_param else today.year
        except (TypeError, ValueError):
            return custom_user_error_response("Month and year must be valid integers.", 400)

        if month < 1 or month > 12:
            return custom_user_error_response("Month must be between 1 and 12.", 400)
        if year < 2000 or year > 2100:
            return custom_user_error_response("Year must be between 2000 and 2100.", 400)

        budgets = wallet.category_budgets.filter(year=year, month=month).select_related('label')

        expenses_by_label = dict(
            Transaction.objects.filter(
                wallet=wallet,
                type='EXPENSE',
                date__year=year,
                date__month=month,
                label__isnull=False,
            ).values('label_id').annotate(total=Sum('value')).values_list('label_id', 'total')
        )

        total_budget = Decimal('0.00')
        total_spent = Decimal('0.00')
        normal_count = 0
        approaching_count = 0
        exceeded_count = 0

        for b in budgets:
            spent = expenses_by_label.get(b.label_id, Decimal('0.00'))
            total_budget += b.amount
            total_spent += spent
            pct = (spent / b.amount * 100) if b.amount > 0 else 0
            if pct > 100:
                exceeded_count += 1
            elif pct >= 80:
                approaching_count += 1
            else:
                normal_count += 1

        total_remaining = max(Decimal('0.00'), total_budget - total_spent)
        overall_percentage = round(float(total_spent / total_budget * 100), 2) if total_budget > 0 else 0.0

        # Total monthly expenses across all categories (including uncategorized/unbudgeted)
        total_monthly_expenses = Transaction.objects.filter(
            wallet=wallet,
            type='EXPENSE',
            date__year=year,
            date__month=month,
        ).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

        unbudgeted_spent = max(Decimal('0.00'), total_monthly_expenses - total_spent)

        return Response({
            'month': month,
            'year': year,
            'total_budget': f"{total_budget:.2f}",
            'total_spent': f"{total_spent:.2f}",
            'total_remaining': f"{total_remaining:.2f}",
            'overall_percentage': overall_percentage,
            'total_monthly_expenses': f"{total_monthly_expenses:.2f}",
            'unbudgeted_spent': f"{unbudgeted_spent:.2f}",
            'budget_count': budgets.count(),
            'status_counts': {
                'normal': normal_count,
                'approaching': approaching_count,
                'exceeded': exceeded_count,
            }
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    user: HubUser = request.user
    transactions: QuerySet

    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    # number of transactions returned
    limit = request.query_params.get('limit')
    # return only values grouped by date for charts
    chart_type = request.query_params.get('chart_type')
    search = request.query_params.get('search') or request.query_params.get('q')

    transactions = user.get_wallet().transactions.all()

    if search and search.strip():
        term = search.strip()
        q_filter = Q(title__icontains=term) | Q(label__name__icontains=term)

        term_upper = term.upper()
        if term_upper in ['EXPENSE', 'CHI', 'KHOẢN CHI', 'KHOAN CHI']:
            q_filter |= Q(type='EXPENSE')
        elif term_upper in ['EARNING', 'THU', 'KHOẢN THU', 'KHOAN THU']:
            q_filter |= Q(type='EARNING')
        elif term_upper in ['RECURRENT', 'RECURRING', 'ĐỊNH KỲ', 'DINH KY', 'LẶP LẠI', 'LAP LAI']:
            q_filter |= Q(recurrent=True)

        clean_numeric = term.replace(',', '').replace('.', '').replace('đ', '').replace('VND', '').strip()
        try:
            val = Decimal(clean_numeric)
            q_filter |= Q(value=val)
        except (InvalidOperation, ValueError):
            pass

        try:
            parsed_d = date.fromisoformat(term)
            q_filter |= Q(date=parsed_d)
        except ValueError:
            pass

        transactions = transactions.filter(q_filter)

    if bool(start_date_str) != bool(end_date_str):
        return custom_user_error_response('Both start_date and end_date are required.', 400)

    if start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return custom_user_error_response('Dates must use YYYY-MM-DD.', 400)
        if start_date > end_date:
            return custom_user_error_response('start_date must not be after end_date.', 400)

        transactions = transactions.filter(date__range=[start_date, end_date])

    try:
        limit = int(limit or 0)
        chart_type = int(chart_type or 0)
    except (TypeError, ValueError):
        return custom_user_error_response('limit and chart_type must be integers.', 400)

    if chart_type == 0:
        transactions = transactions.order_by('-date', '-id')
        if limit > 0:
            transactions = transactions[:limit]
        transactions_serialized = TransactionSerializer(transactions, many=True)
        return Response(transactions_serialized.data)

    if chart_type == 1:
        # CHART TYPE == 1: Bar chart grouping by dates
        if not (start_date_str and end_date_str):
            return custom_user_error_response('Date range is required for this chart.', 400)
        grouped_transactions_list = transactions.expenses().group_by_dates().add_empty_dates(start_date, end_date)

    elif chart_type == 2:
        # CHART TYPE == 2: Pie chart grouping by labels
        grouped_transactions_list = transactions.expenses().group_by_labels()

    else:
        return custom_user_error_response('chart_type must be 0, 1, or 2.', 400)

    return Response(grouped_transactions_list)
