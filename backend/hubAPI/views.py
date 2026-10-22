import os
import re
import datetime
import calendar
import unicodedata
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.db.models import QuerySet, Sum, Q
from .utils import custom_server_error_response, custom_success_response, custom_user_error_response
from hubModels.serializers import MyTokenObtainPairSerializer, MyTokenRefreshSerializer
from hubModels.models import (HubUser, Transaction, CustomLabel, SavingPlan, CategoryBudget,
                              SavingPlanContribution, DebtLoan, DebtPayment)
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
import uuid
from rest_framework.parsers import FileUploadParser
from hubModels.serializers import (SavingPlanSerializer, WalletSerializer, TransactionSerializer,
                                  CategoryBudgetSerializer, SavingPlanContributionSerializer,
                                  DebtLoanSerializer, DebtPaymentSerializer)

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from datetime import date
from datetime import timedelta
from hubModels.models import CustomLabel
from hubModels.serializers import LabelSerializer
from hubModels.importer import InvoiceImporter, PDFInvoiceImporter, InvoiceProcessingException, parse_date
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
                transaction = Transaction.objects.select_for_update(of=('self',)).get(
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


ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp', '.heic', '.tiff', '.bmp'}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB per file


class ImportInvoicesAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user: HubUser = request.user

        files_list = request.FILES.getlist('files[]')
        if not files_list:
            return custom_user_error_response("Vui lòng chọn ít nhất một tệp để tải lên.", 400)

        for uploaded_file in files_list:
            _, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower()
            if not ext or ext not in ALLOWED_UPLOAD_EXTENSIONS:
                return custom_user_error_response(
                    f"Định dạng tệp '{uploaded_file.name}' không được hỗ trợ. Vui lòng chỉ tải lên tệp PDF hoặc ảnh (PNG, JPG, WEBP).",
                    400
                )
            if uploaded_file.size > MAX_UPLOAD_SIZE:
                return custom_user_error_response(
                    f"Tệp '{uploaded_file.name}' vượt quá dung lượng tối đa cho phép (10MB).",
                    400
                )

        institution = request.query_params.get('institution')
        update_wallet = request.query_params.get('updateWallet') in ['1', 'true', 'True', True]
        transaction_type = request.query_params.get('type', None)
        label_id = request.query_params.get('label', None)

        if update_wallet and not transaction_type:
            # Update wallet has no effect if transaction type is None
            update_wallet = False

        os.makedirs('hubAPI/imported_files', exist_ok=True)
        imported_items = []

        for uploaded_file in files_list:
            _, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower() or '.pdf'
            file_name = f"buffer_{user.pk}_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join('hubAPI', 'imported_files', file_name)

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
                    tx = Transaction.create_from_import(imported_data=invoice_dict, optional_data=optional_data, user=user)
                    val_num = float(tx.value) if tx.value is not None else 0.0
                    val_str = f"{val_num:,.0f} đ".replace(',', '.')
                    date_str = tx.date.strftime('%d/%m/%Y') if tx.date else ''
                    imported_items.append({
                        'id': tx.id,
                        'title': tx.title,
                        'value': val_num,
                        'formatted_value': val_str,
                        'date': date_str,
                    })
                except Exception as e:
                    return custom_user_error_response('Có lỗi xảy ra khi lưu giao dịch từ hoá đơn. Vui lòng thử lại.')
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return Response({
            'success': True,
            'message': 'Đã nhập hoá đơn thành công! Vui lòng cập nhật các thông tin còn thiếu.',
            'imported': imported_items,
        }, status=200)


class ImportPreviewAPIView(APIView):
    """
    API trích xuất và đọc thông tin từ ảnh biên lai / PDF trước khi lưu giao dịch.
    Trả về dữ liệu đã đọc được (tiêu đề, số tiền, ngày tháng, định dạng) để hiển thị thông báo trực quan cho người dùng.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user: HubUser = request.user
        files_list = request.FILES.getlist('files[]')
        institution = request.query_params.get('institution')

        if not files_list:
            return custom_user_error_response('Vui lòng chọn ít nhất một tệp để phân tích.', 400)

        for uploaded_file in files_list:
            _, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower()
            if not ext or ext not in ALLOWED_UPLOAD_EXTENSIONS:
                return custom_user_error_response(
                    f"Định dạng tệp '{uploaded_file.name}' không được hỗ trợ. Vui lòng chỉ tải lên tệp PDF hoặc ảnh (PNG, JPG, WEBP).",
                    400
                )
            if uploaded_file.size > MAX_UPLOAD_SIZE:
                return custom_user_error_response(
                    f"Tệp '{uploaded_file.name}' vượt quá dung lượng tối đa cho phép (10MB).",
                    400
                )

        os.makedirs('hubAPI/imported_files', exist_ok=True)
        parsed_results = []

        for idx, uploaded_file in enumerate(files_list):
            _, ext = os.path.splitext(uploaded_file.name)
            ext = ext.lower() or '.pdf'
            file_name = f"preview_{user.pk}_{idx}_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join('hubAPI', 'imported_files', file_name)

            try:
                with open(file_path, 'wb') as file:
                    for chunk in uploaded_file.chunks():
                        file.write(chunk)

                try:
                    invoice_dict = InvoiceImporter(file_path, institution).process_file()
                except Exception as e:
                    invoice_dict = {'value': None, 'date': None, 'title': None}

                val = invoice_dict.get('value')
                date_val = invoice_dict.get('date')
                title = invoice_dict.get('title')

                formatted_date = ''
                if isinstance(date_val, (datetime.date, datetime.datetime)):
                    formatted_date = date_val.strftime('%d/%m/%Y')
                elif date_val:
                    d_parsed = parse_date(str(date_val))
                    formatted_date = d_parsed.strftime('%d/%m/%Y') if d_parsed else str(date_val)

                val_num = None
                formatted_val = ''
                if val is not None:
                    try:
                        val_num = float(val)
                        formatted_val = f"{val_num:,.0f} đ".replace(',', '.')
                    except (ValueError, TypeError):
                        pass

                parsed_results.append({
                    'file_name': uploaded_file.name,
                    'title': title or 'Giao dịch chuyển khoản',
                    'value': val_num,
                    'formatted_value': formatted_val,
                    'date': str(date_val) if date_val else '',
                    'formatted_date': formatted_date,
                    'institution': institution or 'Ngân hàng Việt Nam (Chung / VietQR)',
                    'is_valid': bool(val_num or formatted_date),
                })
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return Response({
            'success': True,
            'message': 'Đã phân tích thông tin hoá đơn thành công.',
            'results': parsed_results,
        }, status=200)



@api_view(['GET'])
@permission_classes([AllowAny])
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
        '/api/reports/summary',
        '/api/reports/transactions',
        '/api/reports/export/csv',
    ]

    return Response(routes)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_user(request):
    data = request.data
    if not isinstance(data, dict):
        return custom_user_error_response("Dữ liệu không hợp lệ.", 400)
    try:
        HubUser.create_from_json(data)
        return Response({"message": "Tạo tài khoản thành công!"}, status=201)
    except ValidationError as e:
        if hasattr(e, 'message_dict'):
            first_err = next(iter(e.message_dict.values()))
            msg = first_err[0] if isinstance(first_err, list) else str(first_err)
        elif hasattr(e, 'message'):
            msg = e.message
        else:
            msg = str(e)
        return custom_user_error_response(msg, 400)
    except Exception as e:
        return custom_user_error_response("Email này đã được sử dụng hoặc thông tin không hợp lệ.", 400)


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
        status_filter = request.query_params.get('status')
        if status_filter:
            plans = [p for p in plans if p.get_status() == status_filter]
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


class SavingPlanContributionAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SavingPlanContributionSerializer

    def get_plan(self, user: HubUser, saving_plan_pk: int):
        try:
            return SavingPlan.objects.get(pk=saving_plan_pk, wallet__user=user)
        except SavingPlan.DoesNotExist:
            return None

    def get(self, request, saving_plan_pk=None, contribution_pk=None):
        user: HubUser = request.user
        plan = self.get_plan(user, saving_plan_pk)
        if not plan:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        if contribution_pk:
            try:
                contrib = plan.contributions.get(pk=contribution_pk, user=user)
                return Response(self.serializer_class(contrib).data)
            except SavingPlanContribution.DoesNotExist:
                return custom_user_error_response("Không tìm thấy khoản đóng góp.", 404)

        contributions = plan.contributions.filter(user=user)
        return Response(self.serializer_class(contributions, many=True).data)

    def post(self, request, saving_plan_pk=None):
        user: HubUser = request.user
        plan = self.get_plan(user, saving_plan_pk)
        if not plan:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        try:
            idempotency_key = request.data.get('idempotency_key') or request.data.get('idempotencyKey')
            if idempotency_key:
                existing = SavingPlanContribution.objects.filter(
                    user=user, idempotency_key=str(idempotency_key).strip()
                ).first()
                if existing:
                    return Response(self.serializer_class(existing).data, status=200)

            contribution = SavingPlanContribution.create_from_json(
                plan_pk=plan.pk,
                user=user,
                data=request.data,
            )
            return Response(self.serializer_class(contribution).data, status=201)
        except ValidationError as error:
            msg = error.message if hasattr(error, 'message') else str(error)
            return custom_user_error_response(msg, 400)
        except SavingPlan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

    def put(self, request, saving_plan_pk=None, contribution_pk=None):
        user: HubUser = request.user
        plan = self.get_plan(user, saving_plan_pk)
        if not plan:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        pk = contribution_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("Thiếu mã khoản đóng góp.", 400)

        try:
            if not plan.contributions.filter(pk=pk, user=user).exists():
                return custom_user_error_response("Không tìm thấy khoản đóng góp.", 404)

            contribution = SavingPlanContribution.update_from_json(pk, user, request.data)
            return Response(self.serializer_class(contribution).data, status=200)
        except SavingPlanContribution.DoesNotExist:
            return custom_user_error_response("Không tìm thấy khoản đóng góp.", 404)
        except ValidationError as error:
            msg = error.message if hasattr(error, 'message') else str(error)
            return custom_user_error_response(msg, 400)

    def delete(self, request, saving_plan_pk=None, contribution_pk=None):
        user: HubUser = request.user
        plan = self.get_plan(user, saving_plan_pk)
        if not plan:
            return custom_user_error_response("Không tìm thấy kế hoạch tiết kiệm.", 404)

        if not contribution_pk:
            return custom_user_error_response("Thiếu mã khoản đóng góp.", 400)

        try:
            contrib = plan.contributions.get(pk=contribution_pk, user=user)
            contrib.delete()
            return custom_success_response("Khoản đóng góp đã được xoá thành công!")
        except SavingPlanContribution.DoesNotExist:
            return custom_user_error_response("Không tìm thấy khoản đóng góp.", 404)


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


def remove_vietnamese_accents(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", text)


NON_ESSENTIAL_KEYWORDS = [
    'giải trí', 'giai tri',
    'cà phê', 'ca phe', 'cafe',
    'mua sắm', 'mua sam',
    'du lịch', 'du lich',
    'tiêu dùng', 'tieu dung',
    'shopping', 'entertainment', 'coffee', 'party', 'leisure',
    'quà tặng', 'qua tang',
    'game',
    'ăn vặt', 'an vat',
    'xem phim',
]


def is_category_non_essential(name: str) -> bool:
    if not name:
        return False
    name_lower = name.lower()
    name_unaccented = remove_vietnamese_accents(name_lower)
    return any(kw in name_lower or kw in name_unaccented for kw in NON_ESSENTIAL_KEYWORDS)


class BudgetCheckImpactAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user: HubUser = request.user
        wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        label_id = request.data.get('label_id') or request.data.get('label')
        if isinstance(label_id, dict):
            label_id = label_id.get('id')

        if not label_id:
            return Response({
                'has_budget': False,
                'budget_amount': '0.00',
                'spent_before': '0.00',
                'spent_after': '0.00',
                'percent_before': 0.0,
                'percent_after': 0.0,
                'overspent_amount': '0.00',
                'status': 'normal',
            })

        # Object-level authorization: ensure label belongs to this user's wallet
        try:
            label = CustomLabel.objects.get(pk=label_id, wallet=wallet)
        except (CustomLabel.DoesNotExist, ValueError, TypeError):
            return custom_user_error_response("Không tìm thấy danh mục.", 404)

        # Parse date
        date_raw = request.data.get('date')
        target_date = date.today()
        if date_raw:
            try:
                target_date = Transaction._parse_date(date_raw)
            except Exception:
                target_date = date.today()

        month = target_date.month
        year = target_date.year

        budget = CategoryBudget.objects.filter(
            wallet=wallet, label=label, month=month, year=year
        ).first()

        if not budget:
            return Response({
                'has_budget': False,
                'budget_amount': '0.00',
                'spent_before': '0.00',
                'spent_after': '0.00',
                'percent_before': 0.0,
                'percent_after': 0.0,
                'overspent_amount': '0.00',
                'status': 'normal',
            })

        spent_before = budget.get_spent()

        val_raw = request.data.get('value', 0)
        try:
            if isinstance(val_raw, str):
                val_raw = val_raw.replace(',', '').replace(' ', '')
            added_val = Decimal(str(val_raw))
            if not added_val.is_finite() or added_val < 0:
                added_val = Decimal('0.00')
        except (InvalidOperation, TypeError, ValueError):
            added_val = Decimal('0.00')

        spent_after = spent_before + added_val
        percent_before = round(float(spent_before / budget.amount) * 100, 2) if budget.amount > 0 else 0.0
        percent_after = round(float(spent_after / budget.amount) * 100, 2) if budget.amount > 0 else 0.0
        overspent_amount = max(Decimal('0.00'), spent_after - budget.amount)

        if percent_after > 100:
            status = 'exceeded'
        elif percent_after >= 80:
            status = 'approaching'
        else:
            status = 'normal'

        return Response({
            'has_budget': True,
            'budget_amount': f"{budget.amount:.2f}",
            'spent_before': f"{spent_before:.2f}",
            'spent_after': f"{spent_after:.2f}",
            'percent_before': percent_before,
            'percent_after': percent_after,
            'overspent_amount': f"{overspent_amount:.2f}",
            'status': status,
        })


class BudgetRebalanceAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user: HubUser = request.user
        wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        data = request.data
        from_label_id = data.get('from_label_id')
        to_label_id = data.get('to_label_id')
        amount_raw = data.get('amount')
        month_raw = data.get('month', date.today().month)
        year_raw = data.get('year', date.today().year)

        if not from_label_id or not to_label_id:
            return custom_user_error_response("Vui lòng cung cấp đầy đủ danh mục nguồn và đích.", 400)

        if str(from_label_id) == str(to_label_id):
            return custom_user_error_response("Danh mục nguồn và danh mục đích không được trùng nhau.", 400)

        try:
            month = int(month_raw)
            year = int(year_raw)
            if month < 1 or month > 12 or year < 2000 or year > 2100:
                raise ValueError
        except (TypeError, ValueError):
            return custom_user_error_response("Tháng và năm không hợp lệ.", 400)

        try:
            if isinstance(amount_raw, str):
                amount_raw = amount_raw.replace(',', '').replace(' ', '')
            amount = Decimal(str(amount_raw))
            if not amount.is_finite() or amount <= 0:
                return custom_user_error_response("Số tiền tái cân bằng phải lớn hơn 0.", 400)
            if len(amount.as_tuple().digits) > 15 or -amount.as_tuple().exponent > 2:
                return custom_user_error_response("Số tiền không hợp lệ (tối đa 15 chữ số và 2 chữ số thập phân).", 400)
        except (InvalidOperation, TypeError, ValueError):
            return custom_user_error_response("Số tiền tái cân bằng không hợp lệ.", 400)

        try:
            with db_transaction.atomic():
                budgets = list(
                    CategoryBudget.objects.select_for_update()
                    .filter(wallet=wallet, month=month, year=year, label_id__in=[from_label_id, to_label_id])
                    .order_by('pk')
                )
                from_budget = next((b for b in budgets if str(b.label_id) == str(from_label_id)), None)
                to_budget = next((b for b in budgets if str(b.label_id) == str(to_label_id)), None)

                if not from_budget:
                    return custom_user_error_response("Không tìm thấy ngân sách nguồn.", 404)

                if not to_budget:
                    return custom_user_error_response("Không tìm thấy ngân sách đích.", 404)

                from_spent = from_budget.get_spent()
                if from_budget.amount - amount < from_spent:
                    return custom_user_error_response("Ngân sách nguồn sau khi giảm không được nhỏ hơn số tiền đã chi.", 400)

                from_budget.amount -= amount
                to_budget.amount += amount
                from_budget.save(update_fields=['amount', 'updated_at'])
                to_budget.save(update_fields=['amount', 'updated_at'])
        except Exception:
            return custom_server_error_response(
                "Đã có lỗi xảy ra trong quá trình xử lý tái cân bằng. Giao dịch đã được hoàn tác.", 500
            )

        return Response({
            'message': 'Tái cân bằng ngân sách thành công!',
            'from_budget': CategoryBudgetSerializer(from_budget).data,
            'to_budget': CategoryBudgetSerializer(to_budget).data,
        })


class BudgetRebalanceSuggestionsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        label_id = request.query_params.get('label_id')
        month_param = request.query_params.get('month')
        year_param = request.query_params.get('year')

        today = date.today()
        try:
            month = int(month_param) if month_param else today.month
            year = int(year_param) if year_param else today.year
        except (TypeError, ValueError):
            return custom_user_error_response("Month and year must be valid integers.", 400)

        if month < 1 or month > 12 or year < 2000 or year > 2100:
            return custom_user_error_response("Month or year outside valid range.", 400)

        deficit = Decimal('0.00')
        if label_id:
            try:
                target_budget = CategoryBudget.objects.get(
                    wallet=wallet, label_id=label_id, month=month, year=year
                )
                target_spent = target_budget.get_spent()
                if target_spent > target_budget.amount:
                    deficit = target_spent - target_budget.amount
            except CategoryBudget.DoesNotExist:
                if not CustomLabel.objects.filter(pk=label_id, wallet=wallet).exists():
                    return custom_user_error_response("Không tìm thấy danh mục.", 404)
                deficit = Decimal('0.00')

        days_in_month = calendar.monthrange(year, month)[1]
        if year > today.year or (year == today.year and month > today.month):
            month_progress = 0.0
        elif year < today.year or (year == today.year and month < today.month):
            month_progress = 1.0
        else:
            month_progress = today.day / days_in_month

        if month_progress <= 0.5:
            return Response([])

        source_budgets_qs = wallet.category_budgets.filter(
            year=year, month=month
        ).select_related('label')

        if label_id:
            source_budgets_qs = source_budgets_qs.exclude(label_id=label_id)

        candidates = []
        for b in source_budgets_qs:
            spent = b.get_spent()
            if b.amount <= 0:
                continue
            spent_ratio = spent / b.amount
            if spent_ratio >= Decimal('0.60'):
                continue

            available_rebalance = max(Decimal('0.00'), b.amount - spent)
            if deficit > 0 and available_rebalance < deficit:
                continue
            if available_rebalance <= 0:
                continue

            candidates.append({
                'budget_id': b.id,
                'label_id': b.label.id,
                'label_name': b.label.name,
                'label_color': b.label.color,
                'amount': f"{b.amount:.2f}",
                'spent': f"{spent:.2f}",
                'available_rebalance': f"{available_rebalance:.2f}",
                'spent_percentage': round(float(spent_ratio * 100), 2),
                'is_non_essential': is_category_non_essential(b.label.name),
            })

        candidates.sort(key=lambda x: (0 if x['is_non_essential'] else 1, -Decimal(x['available_rebalance'])))

        return Response(candidates)


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


class DebtAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DebtLoanSerializer

    def get(self, request, debt_pk=None):
        user: HubUser = request.user
        if debt_pk:
            try:
                debt = DebtLoan.objects.get(pk=debt_pk, wallet__user=user)
                return Response(self.serializer_class(debt).data)
            except DebtLoan.DoesNotExist:
                return custom_user_error_response("Không tìm thấy hợp đồng nợ.", 404)

        debts = user.get_debts()
        type_filter = request.query_params.get('type')
        if type_filter:
            debts = debts.filter(type=type_filter)

        status_filter = request.query_params.get('status')
        if status_filter:
            debts = [d for d in debts if d.get_computed_status() == status_filter]

        return Response(self.serializer_class(debts, many=True).data)

    def post(self, request):
        user: HubUser = request.user
        try:
            debt = DebtLoan.create_from_json(request.data, user_pk=user.pk)
            return Response(self.serializer_class(debt).data, status=201)
        except ValidationError as error:
            msg = error.message_dict if hasattr(error, 'message_dict') else (error.message if hasattr(error, 'message') else str(error))
            return custom_user_error_response(msg, 400)
        except PermissionError as error:
            return custom_user_error_response(str(error), 404)

    def put(self, request, debt_pk=None):
        user: HubUser = request.user
        pk = debt_pk or request.data.get('id')
        if not pk:
            return custom_user_error_response("Mã hợp đồng nợ là bắt buộc.", 400)

        try:
            debt = DebtLoan.update_from_json(pk, user, request.data)
            return Response(self.serializer_class(debt).data, status=200)
        except DebtLoan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy hợp đồng nợ.", 404)
        except ValidationError as error:
            msg = error.message_dict if hasattr(error, 'message_dict') else (error.message if hasattr(error, 'message') else str(error))
            return custom_user_error_response(msg, 400)

    def delete(self, request, debt_pk=None):
        user: HubUser = request.user
        if not debt_pk:
            return custom_user_error_response("Mã hợp đồng nợ là bắt buộc.", 400)

        try:
            debt = DebtLoan.objects.get(pk=debt_pk, wallet__user=user)
        except DebtLoan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy hợp đồng nợ.", 404)

        try:
            debt.delete()
        except DebtLoan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy hợp đồng nợ.", 404)
        except ValidationError as error:
            msg = error.message_dict if hasattr(error, 'message_dict') else (error.message if hasattr(error, 'message') else str(error))
            return custom_user_error_response(msg, 400)
        return custom_success_response("Hợp đồng nợ đã được xoá thành công!")


class DebtPaymentAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = DebtPaymentSerializer

    def get(self, request, debt_pk=None, payment_pk=None):
        user: HubUser = request.user
        try:
            debt = DebtLoan.objects.get(pk=debt_pk, wallet__user=user)
        except DebtLoan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy hợp đồng nợ.", 404)

        if payment_pk:
            try:
                payment = debt.payments.get(pk=payment_pk)
                return Response(self.serializer_class(payment).data)
            except DebtPayment.DoesNotExist:
                return custom_user_error_response("Không tìm thấy khoản thanh toán.", 404)

        return Response(self.serializer_class(debt.payments.all(), many=True).data)

    def post(self, request, debt_pk=None):
        user: HubUser = request.user
        try:
            payment = DebtPayment.create_from_json(debt_pk, user, request.data)
            return Response(self.serializer_class(payment).data, status=201)
        except DebtLoan.DoesNotExist:
            return custom_user_error_response("Không tìm thấy hợp đồng nợ.", 404)
        except ValidationError as error:
            msg = error.message_dict if hasattr(error, 'message_dict') else (error.message if hasattr(error, 'message') else str(error))
            return custom_user_error_response(msg, 400)
        except PermissionError as error:
            return custom_user_error_response(str(error), 404)

    def put(self, request, debt_pk=None, payment_pk=None):
        user: HubUser = request.user
        pid = payment_pk or request.data.get('id')
        if not pid:
            return custom_user_error_response("Mã thanh toán là bắt buộc.", 400)

        try:
            payment = DebtPayment.update_from_json(pid, user, request.data)
            return Response(self.serializer_class(payment).data, status=200)
        except DebtPayment.DoesNotExist:
            return custom_user_error_response("Không tìm thấy khoản thanh toán.", 404)
        except ValidationError as error:
            msg = error.message_dict if hasattr(error, 'message_dict') else (error.message if hasattr(error, 'message') else str(error))
            return custom_user_error_response(msg, 400)
        except PermissionError as error:
            return custom_user_error_response(str(error), 404)

    def delete(self, request, debt_pk=None, payment_pk=None):
        user: HubUser = request.user
        if not payment_pk:
            return custom_user_error_response("Mã thanh toán là bắt buộc.", 400)

        try:
            DebtPayment.delete_payment(payment_pk, user)
            return custom_success_response("Khoản thanh toán đã được xoá thành công!")
        except DebtPayment.DoesNotExist:
            return custom_user_error_response("Không tìm thấy khoản thanh toán.", 404)
        except PermissionError as error:
            return custom_user_error_response(str(error), 404)


class DebtSummaryAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        debts = user.get_debts()
        today = date.today()
        in_7_days = today + timedelta(days=7)

        total_loan_given_remaining = Decimal('0.00')
        total_debt_borrowed_remaining = Decimal('0.00')
        due_in_7_days_count = 0
        overdue_count = 0

        for debt in debts:
            remaining = debt.get_remaining_amount()
            if remaining > Decimal('0.00'):
                if debt.type == 'LOAN_GIVEN':
                    total_loan_given_remaining += remaining
                elif debt.type in ('DEBT_BORROWED', 'INSTALLMENT'):
                    total_debt_borrowed_remaining += remaining

                if debt.due_date:
                    if debt.due_date < today:
                        overdue_count += 1
                    elif today <= debt.due_date <= in_7_days:
                        due_in_7_days_count += 1

        return Response({
            'total_loan_given_remaining': f"{total_loan_given_remaining:.2f}",
            'total_debt_borrowed_remaining': f"{total_debt_borrowed_remaining:.2f}",
            'due_in_7_days_count': due_in_7_days_count,
            'overdue_count': overdue_count,
            'total_debts_count': debts.count(),
        })


class CashFlowForecastAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Không tìm thấy ví của người dùng.", 404)

        days_param = request.query_params.get('days')
        safety_buffer_param = request.query_params.get('safety_buffer')

        # Validate days (30, 60, 90; default 30)
        if days_param in (None, ''):
            days = 30
        else:
            try:
                days = int(days_param)
            except (ValueError, TypeError):
                return custom_user_error_response("Khoảng thời gian dự báo phải là số nguyên (30, 60 hoặc 90 ngày).", 400)

            if days not in (30, 60, 90):
                return custom_user_error_response("Khoảng thời gian dự báo phải là 30, 60 hoặc 90 ngày.", 400)

        # Validate safety_buffer (Decimal >= 0; default 0)
        if safety_buffer_param in (None, ''):
            safety_buffer = Decimal('0.00')
        else:
            try:
                safety_buffer = Decimal(str(safety_buffer_param))
            except (InvalidOperation, ValueError, TypeError):
                return custom_user_error_response("Ngưỡng an toàn phải là số không âm hợp lệ.", 400)

            if not safety_buffer.is_finite() or safety_buffer < Decimal('0.00'):
                return custom_user_error_response("Ngưỡng an toàn phải là số không âm hợp lệ.", 400)

        from hubModels.services import CashFlowForecastService
        result = CashFlowForecastService.forecast(
            wallet=wallet,
            days=days,
            safety_buffer=safety_buffer,
        )

        return Response(result.to_dict())


