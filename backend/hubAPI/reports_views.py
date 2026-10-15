import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hubModels.models import CustomLabel, HubUser, Transaction, Wallet
from hubModels.serializers import TransactionSerializer
from .utils import custom_user_error_response



def sanitize_csv_cell(value):
    """
    Prevents CSV Formula Injection (Excel Macro / Command Injection).
    If a string starts with =, +, -, @, tab, or carriage return,
    prefix it with a single quote (').
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + val_str
    return val_str


class ReportSummaryAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet: Wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tx_type = request.query_params.get('type')  # ALL, EXPENSE, EARNING
        label_id_param = request.query_params.get('label_id') or request.query_params.get('label')
        wallet_id_param = request.query_params.get('wallet_id') or request.query_params.get('wallet')

        # Wallet validation if provided
        if wallet_id_param:
            try:
                wallet_id = int(wallet_id_param)
                if wallet.id != wallet_id:
                    return custom_user_error_response("You do not have access to this wallet.", 403)
            except (ValueError, TypeError):
                return custom_user_error_response("Invalid wallet_id.", 400)

        # Date parsing and defaults
        today = date.today()
        if not start_date_str and not end_date_str:
            # Default to current month
            start_date = date(today.year, today.month, 1)
            # Find last day of current month
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        elif bool(start_date_str) != bool(end_date_str):
            return custom_user_error_response("Both start_date and end_date are required when specifying a date range.", 400)
        else:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                return custom_user_error_response("Dates must use YYYY-MM-DD format.", 400)

            if start_date > end_date:
                return custom_user_error_response("start_date must not be after end_date.", 400)

        days_count = (end_date - start_date).days + 1

        # Current period base queryset
        tx_base = wallet.transactions.filter(date__range=[start_date, end_date])

        # Optional label filtering
        label_id = None
        if label_id_param:
            try:
                label_id = int(label_id_param)
                # Verify label belongs to user's wallet
                if not CustomLabel.objects.filter(pk=label_id, wallet=wallet).exists():
                    return custom_user_error_response("Category was not found in your wallet.", 404)
            except (ValueError, TypeError):
                return custom_user_error_response("Invalid label_id.", 400)

        # Income & Expense Totals
        income_qs = tx_base.filter(type='EARNING')
        expense_qs = tx_base.filter(type='EXPENSE')

        if label_id:
            income_qs = income_qs.filter(label_id=label_id)
            expense_qs = expense_qs.filter(label_id=label_id)

        total_income = income_qs.aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        total_expense = expense_qs.aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        net_cash_flow = total_income - total_expense

        avg_daily_spending = round(total_expense / Decimal(days_count), 2) if days_count > 0 else Decimal('0.00')

        # Previous equivalent period calculation
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_count - 1)

        prev_base = wallet.transactions.filter(date__range=[prev_start, prev_end])
        prev_income_qs = prev_base.filter(type='EARNING')
        prev_expense_qs = prev_base.filter(type='EXPENSE')

        if label_id:
            prev_income_qs = prev_income_qs.filter(label_id=label_id)
            prev_expense_qs = prev_expense_qs.filter(label_id=label_id)

        prev_income = prev_income_qs.aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        prev_expense = prev_expense_qs.aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        prev_net = prev_income - prev_expense

        # Percentage comparison calculations
        def calc_pct_change(current, previous):
            if previous > 0:
                return round(float((current - previous) / previous * 100), 2)
            if previous == 0 and current > 0:
                return 100.0
            return 0.0

        def calc_net_pct_change(current, previous):
            if previous != 0:
                return round(float((current - previous) / abs(previous) * 100), 2)
            if previous == 0 and current != 0:
                return 100.0 if current > 0 else -100.0
            return 0.0

        income_change_pct = calc_pct_change(total_income, prev_income)
        expense_change_pct = calc_pct_change(total_expense, prev_expense)
        net_change_pct = calc_net_pct_change(net_cash_flow, prev_net)

        # Category spending breakdown (for expenses)
        # Groups all expenses in the current period by label
        labeled_breakdown = list(
            tx_base.filter(type='EXPENSE', label__isnull=False)
            .values('label_id', 'label__name', 'label__color')
            .annotate(total=Sum('value'), count=Count('id'))
            .order_by('-total')
        )

        unlabeled_expense = tx_base.filter(type='EXPENSE', label__isnull=True).aggregate(
            total=Sum('value'), count=Count('id')
        )
        if unlabeled_expense['total'] and unlabeled_expense['total'] > 0:
            labeled_breakdown.append({
                'label_id': None,
                'label__name': 'Chưa phân loại',
                'label__color': '#6c757d',
                'total': unlabeled_expense['total'],
                'count': unlabeled_expense['count'],
            })

        category_breakdown = []
        for item in labeled_breakdown:
            amount = item['total']
            pct = round(float(amount / total_expense * 100), 2) if total_expense > 0 else 0.0
            category_breakdown.append({
                'label_id': item['label_id'],
                'label_name': item['label__name'],
                'label_color': item['label__color'] or '#00863A',
                'total': f"{amount:.2f}",
                'percentage': pct,
                'transaction_count': item['count'],
            })

        # Categories with largest spending increases
        # Compare current category expenses vs previous period expenses
        prev_expenses_by_label = dict(
            prev_base.filter(type='EXPENSE', label__isnull=False)
            .values('label_id')
            .annotate(total=Sum('value'))
            .values_list('label_id', 'total')
        )
        prev_unlabeled_val = prev_base.filter(type='EXPENSE', label__isnull=True).aggregate(total=Sum('value'))['total'] or Decimal('0.00')

        spending_increases = []
        for item in category_breakdown:
            l_id = item['label_id']
            curr_val = Decimal(item['total'])
            prev_val = prev_expenses_by_label.get(l_id, Decimal('0.00')) if l_id is not None else prev_unlabeled_val
            diff = curr_val - prev_val
            if diff > 0:
                pct_inc = round(float(diff / prev_val * 100), 1) if prev_val > 0 else 100.0
                spending_increases.append({
                    'label_id': l_id,
                    'label_name': item['label_name'],
                    'label_color': item['label_color'],
                    'current_spent': f"{curr_val:.2f}",
                    'previous_spent': f"{prev_val:.2f}",
                    'increase_amount': f"{diff:.2f}",
                    'increase_percentage': pct_inc,
                })
        spending_increases.sort(key=lambda x: Decimal(x['increase_amount']), reverse=True)

        # Monthly Trends (last 6 months up to end_date)
        trend_start = date(start_date.year, start_date.month, 1) - timedelta(days=150)
        trend_start = date(trend_start.year, trend_start.month, 1)

        trend_txs = wallet.transactions.filter(date__gte=trend_start, date__lte=end_date)
        
        # Build month by month sequence
        monthly_trends = []
        cur_year, cur_month = trend_start.year, trend_start.month
        while (cur_year < end_date.year) or (cur_year == end_date.year and cur_month <= end_date.month):
            m_income = trend_txs.filter(date__year=cur_year, date__month=cur_month, type='EARNING').aggregate(total=Sum('value'))['total'] or Decimal('0.00')
            m_expense = trend_txs.filter(date__year=cur_year, date__month=cur_month, type='EXPENSE').aggregate(total=Sum('value'))['total'] or Decimal('0.00')
            monthly_trends.append({
                'month': cur_month,
                'year': cur_year,
                'label': f"{cur_month:02d}/{cur_year}",
                'income': f"{m_income:.2f}",
                'expense': f"{m_expense:.2f}",
                'net': f"{(m_income - m_expense):.2f}",
            })
            if cur_month == 12:
                cur_year += 1
                cur_month = 1
            else:
                cur_month += 1

        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days_count': days_count,
            },
            'summary': {
                'total_income': f"{total_income:.2f}",
                'total_expense': f"{total_expense:.2f}",
                'net_cash_flow': f"{net_cash_flow:.2f}",
                'average_daily_spending': f"{avg_daily_spending:.2f}",
            },
            'comparison': {
                'previous_period': {
                    'start_date': prev_start.isoformat(),
                    'end_date': prev_end.isoformat(),
                    'total_income': f"{prev_income:.2f}",
                    'total_expense': f"{prev_expense:.2f}",
                    'net_cash_flow': f"{prev_net:.2f}",
                },
                'income_change_percentage': income_change_pct,
                'expense_change_percentage': expense_change_pct,
                'net_cash_flow_change_percentage': net_change_pct,
            },
            'category_breakdown': category_breakdown,
            'largest_spending_increases': spending_increases[:5],
            'monthly_trends': monthly_trends,
        })


class ReportTransactionsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet: Wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tx_type = request.query_params.get('type')
        label_id_param = request.query_params.get('label_id') or request.query_params.get('label')
        search = request.query_params.get('search') or request.query_params.get('q')

        tx_qs = wallet.transactions.all()

        if start_date_str and end_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
                if start_date > end_date:
                    return custom_user_error_response("start_date must not be after end_date.", 400)
                tx_qs = tx_qs.filter(date__range=[start_date, end_date])
            except ValueError:
                return custom_user_error_response("Dates must use YYYY-MM-DD format.", 400)

        if tx_type and tx_type.upper() in ['EXPENSE', 'EARNING']:
            tx_qs = tx_qs.filter(type=tx_type.upper())

        if label_id_param:
            try:
                label_id = int(label_id_param)
                tx_qs = tx_qs.filter(label_id=label_id)
            except ValueError:
                return custom_user_error_response("Invalid label_id.", 400)

        if search and search.strip():
            term = search.strip()
            tx_qs = tx_qs.filter(Q(title__icontains=term) | Q(label__name__icontains=term))

        tx_qs = tx_qs.select_related('label').order_by('-date', '-id')
        serializer = TransactionSerializer(tx_qs, many=True)
        return Response(serializer.data)


class ReportExportCSVAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet: Wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tx_type = request.query_params.get('type')
        label_id_param = request.query_params.get('label_id') or request.query_params.get('label')

        today = date.today()
        if not start_date_str and not end_date_str:
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        elif bool(start_date_str) != bool(end_date_str):
            return custom_user_error_response("Both start_date and end_date are required.", 400)
        else:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
                if start_date > end_date:
                    return custom_user_error_response("start_date must not be after end_date.", 400)
            except ValueError:
                return custom_user_error_response("Dates must use YYYY-MM-DD format.", 400)

        tx_qs = wallet.transactions.filter(date__range=[start_date, end_date])

        if tx_type and tx_type.upper() in ['EXPENSE', 'EARNING']:
            tx_qs = tx_qs.filter(type=tx_type.upper())

        if label_id_param:
            try:
                label_id = int(label_id_param)
                tx_qs = tx_qs.filter(label_id=label_id)
            except ValueError:
                return custom_user_error_response("Invalid label_id.", 400)

        tx_qs = tx_qs.select_related('label').order_by('-date', '-id')

        # Compute summary
        total_income = wallet.transactions.filter(date__range=[start_date, end_date], type='EARNING').aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        total_expense = wallet.transactions.filter(date__range=[start_date, end_date], type='EXPENSE').aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        net_flow = total_income - total_expense

        # Build CSV buffer with UTF-8 BOM (\ufeff) and sep=, directive for Excel compatibility
        output = StringIO()
        output.write('\ufeff')  # UTF-8 BOM
        output.write('sep=,\r\n')  # Tell Excel to split by comma
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Report Header metadata
        writer.writerow(["BÁO CÁO TÀI CHÍNH MONEYMANAGER"])
        writer.writerow([f"Kỳ báo cáo: {start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}"])
        writer.writerow([f"Ngày xuất báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"])
        writer.writerow([f"Người dùng: {sanitize_csv_cell(user.first_name + ' ' + user.last_name)} ({sanitize_csv_cell(user.email)})"])
        writer.writerow([f"Tổng thu nhập: {total_income:,.0f} đ".replace(',', '.')])
        writer.writerow([f"Tổng chi tiêu: {total_expense:,.0f} đ".replace(',', '.')])
        writer.writerow([f"Dòng tiền ròng: {net_flow:,.0f} đ".replace(',', '.')])
        writer.writerow([])

        # Table Column Headers
        writer.writerow([
            "Mã GD",
            "Ngày",
            "Tiêu đề",
            "Loại",
            "Danh mục",
            "Số tiền (VND)",
            "Định kỳ",
            "Nhập từ hoá đơn",
        ])

        # Rows
        for tx in tx_qs:
            type_display = "Khoản thu" if tx.type == "EARNING" else "Khoản chi"
            label_name = tx.label.name if tx.label else "Chưa phân loại"
            formatted_val = f"{tx.value:,.0f}".replace(',', '.')
            writer.writerow([
                sanitize_csv_cell(tx.id),
                sanitize_csv_cell(tx.date.strftime('%d/%m/%Y')),
                sanitize_csv_cell(tx.title),
                sanitize_csv_cell(type_display),
                sanitize_csv_cell(label_name),
                sanitize_csv_cell(formatted_val),
                "Có" if tx.recurrent else "Không",
                "Có" if tx.imported else "Không",
            ])

        csv_content = output.getvalue()
        output.close()

        filename = f"bao_cao_tai_chinh_{start_date.isoformat()}_{end_date.isoformat()}.csv"
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class ReportExportExcelAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user: HubUser = request.user
        wallet: Wallet = user.get_wallet()
        if not wallet:
            return custom_user_error_response("Wallet was not found.", 404)

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        tx_type = request.query_params.get('type')
        label_id_param = request.query_params.get('label_id') or request.query_params.get('label')

        today = date.today()
        if not start_date_str and not end_date_str:
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        elif bool(start_date_str) != bool(end_date_str):
            return custom_user_error_response("Both start_date and end_date are required.", 400)
        else:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
                if start_date > end_date:
                    return custom_user_error_response("start_date must not be after end_date.", 400)
            except ValueError:
                return custom_user_error_response("Dates must use YYYY-MM-DD format.", 400)

        tx_qs = wallet.transactions.filter(date__range=[start_date, end_date])

        if tx_type and tx_type.upper() in ['EXPENSE', 'EARNING']:
            tx_qs = tx_qs.filter(type=tx_type.upper())

        if label_id_param:
            try:
                label_id = int(label_id_param)
                tx_qs = tx_qs.filter(label_id=label_id)
            except ValueError:
                return custom_user_error_response("Invalid label_id.", 400)

        tx_qs = tx_qs.select_related('label').order_by('-date', '-id')

        # Summary figures
        total_income = wallet.transactions.filter(date__range=[start_date, end_date], type='EARNING').aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        total_expense = wallet.transactions.filter(date__range=[start_date, end_date], type='EXPENSE').aggregate(total=Sum('value'))['total'] or Decimal('0.00')
        net_flow = total_income - total_expense

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Báo cáo tài chính"
        ws.views.sheetView[0].showGridLines = True

        font_family = "Arial"
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1'),
        )

        # Title Row
        ws.merge_cells('A2:H2')
        title_cell = ws['A2']
        title_cell.value = "BÁO CÁO TÀI CHÍNH MONEYMANAGER"
        title_cell.font = Font(name=font_family, size=15, bold=True, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="00863A", end_color="00863A", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[2].height = 42

        # Subtitle / Metadata block
        meta_data = [
            ("Kỳ báo cáo:", f"{start_date.strftime('%d/%m/%Y')} đến {end_date.strftime('%d/%m/%Y')}",
             "Tổng thu nhập:", f"+{total_income:,.0f} đ".replace(',', '.'), "15803D"),
            ("Ngày xuất:", datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
             "Tổng chi tiêu:", f"-{total_expense:,.0f} đ".replace(',', '.'), "DC2626"),
            ("Người dùng:", f"{user.first_name} {user.last_name} ({user.email})".strip(),
             "Dòng tiền ròng:", f"{net_flow:,.0f} đ".replace(',', '.'), "15803D" if net_flow >= 0 else "DC2626"),
        ]

        for i, (label_left, val_left, label_right, val_right, color_right) in enumerate(meta_data, start=4):
            ws.row_dimensions[i].height = 22

            # Left key-value
            c_lbl_l = ws.cell(row=i, column=1, value=label_left)
            c_lbl_l.font = Font(name=font_family, size=10, bold=True, color="475569")
            c_lbl_l.alignment = Alignment(horizontal="right", vertical="center")

            ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=3)
            c_val_l = ws.cell(row=i, column=2, value=val_left)
            c_val_l.font = Font(name=font_family, size=10, color="0F172A")
            c_val_l.alignment = Alignment(horizontal="left", vertical="center")

            # Right key-value
            ws.merge_cells(start_row=i, start_column=4, end_row=i, end_column=5)
            c_lbl_r = ws.cell(row=i, column=4, value=label_right)
            c_lbl_r.font = Font(name=font_family, size=10, bold=True, color="475569")
            c_lbl_r.alignment = Alignment(horizontal="right", vertical="center")

            ws.merge_cells(start_row=i, start_column=6, end_row=i, end_column=8)
            c_val_r = ws.cell(row=i, column=6, value=val_right)
            c_val_r.font = Font(name=font_family, size=10, bold=True, color=color_right)
            c_val_r.alignment = Alignment(horizontal="left", vertical="center")

        ws.row_dimensions[7].height = 14

        # Table Headers (Row 8)
        headers = [
            ("Mã GD", 10, Alignment(horizontal="center", vertical="center")),
            ("Ngày", 14, Alignment(horizontal="center", vertical="center")),
            ("Tiêu đề", 28, Alignment(horizontal="left", vertical="center")),
            ("Loại", 14, Alignment(horizontal="center", vertical="center")),
            ("Danh mục", 18, Alignment(horizontal="left", vertical="center")),
            ("Số tiền (VND)", 18, Alignment(horizontal="right", vertical="center")),
            ("Định kỳ", 12, Alignment(horizontal="center", vertical="center")),
            ("Nhập từ hoá đơn", 18, Alignment(horizontal="center", vertical="center")),
        ]

        ws.row_dimensions[8].height = 28
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")

        for col_idx, (col_name, col_width, col_align) in enumerate(headers, start=1):
            cell = ws.cell(row=8, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = col_align
            cell.border = thin_border
            ws.column_dimensions[get_column_letter(col_idx)].width = col_width

        # Rows
        row_idx = 9
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        tx_count = tx_qs.count()
        for tx in tx_qs:
            ws.row_dimensions[row_idx].height = 22
            fill = zebra_fill if row_idx % 2 == 1 else white_fill
            type_display = "Khoản thu" if tx.type == "EARNING" else "Khoản chi"
            type_color = "15803D" if tx.type == "EARNING" else "DC2626"
            label_name = tx.label.name if tx.label else "Chưa phân loại"

            row_data = [
                (tx.id, Alignment(horizontal="center", vertical="center"), Font(name=font_family, size=10)),
                (tx.date.strftime('%d/%m/%Y'), Alignment(horizontal="center", vertical="center"), Font(name=font_family, size=10)),
                (sanitize_csv_cell(tx.title), Alignment(horizontal="left", vertical="center"), Font(name=font_family, size=10)),
                (type_display, Alignment(horizontal="center", vertical="center"), Font(name=font_family, size=10, bold=True, color=type_color)),
                (label_name, Alignment(horizontal="left", vertical="center"), Font(name=font_family, size=10)),
                (float(tx.value), Alignment(horizontal="right", vertical="center"), Font(name=font_family, size=10, bold=True)),
                ("Có" if tx.recurrent else "Không", Alignment(horizontal="center", vertical="center"), Font(name=font_family, size=10)),
                ("Có" if tx.imported else "Không", Alignment(horizontal="center", vertical="center"), Font(name=font_family, size=10)),
            ]

            for col_idx, (val, align, font) in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = font
                cell.alignment = align
                cell.fill = fill
                cell.border = thin_border
                if col_idx == 6:  # Số tiền
                    cell.number_format = '#,##0'

            row_idx += 1

        # Summary total row
        ws.row_dimensions[row_idx].height = 26
        ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=5)
        tot_label = ws.cell(row=row_idx, column=1, value=f"TỔNG CỘNG ({tx_count} giao dịch)")
        tot_label.font = Font(name=font_family, size=10, bold=True, color="0F172A")
        tot_label.alignment = Alignment(horizontal="right", vertical="center")
        tot_label.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        for col_idx in range(1, 6):
            ws.cell(row=row_idx, column=col_idx).border = thin_border
            ws.cell(row=row_idx, column=col_idx).fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        tot_val = ws.cell(row=row_idx, column=6)
        if row_idx > 9:
            tot_val.value = f"=SUM(F9:F{row_idx-1})"
        else:
            tot_val.value = 0
        tot_val.font = Font(name=font_family, size=10, bold=True, color="0F172A")
        tot_val.alignment = Alignment(horizontal="right", vertical="center")
        tot_val.number_format = '#,##0'
        tot_val.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
        tot_val.border = thin_border

        for col_idx in (7, 8):
            c_empty = ws.cell(row=row_idx, column=col_idx, value="")
            c_empty.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
            c_empty.border = thin_border

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        filename = f"bao_cao_tai_chinh_{start_date.isoformat()}_{end_date.isoformat()}.xlsx"
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

