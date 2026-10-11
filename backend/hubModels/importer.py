import datetime
import re
from abc import abstractmethod, ABC
from pypdf import PdfReader
from typing import Dict, Optional


class InvoiceProcessingException(Exception):
    message = 'Không thể phân tích hoá đơn. Vui lòng kiểm tra lại ngân hàng hoặc định dạng tệp PDF.'


def parse_date(date_val) -> Optional[datetime.date]:
    if isinstance(date_val, datetime.datetime):
        return date_val.date()
    if isinstance(date_val, datetime.date):
        return date_val
    if not isinstance(date_val, str):
        return None

    date_str = date_val.strip()
    formats = [
        "%d/%m/%Y - %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y - %H:%M",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y",
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Regex search for DD/MM/YYYY or YYYY-MM-DD inside date_str
    m = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', date_str)
    if m:
        day, month, year = m.groups()
        try:
            return datetime.date(int(year), int(month), int(day))
        except ValueError:
            pass

    m2 = re.search(r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})', date_str)
    if m2:
        year, month, day = m2.groups()
        try:
            return datetime.date(int(year), int(month), int(day))
        except ValueError:
            pass

    return None


def parse_amount(val) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return 0.0

    val = val.strip()
    # Remove currency words: VND, VNĐ, đ, Đ, R$, USD, etc.
    cleaned = re.sub(r'[^\d.,]', '', val)
    if not cleaned:
        return 0.0

    # Handle dots and commas (e.g., 150.000 or 1,500,000 or 150.000,00)
    if '.' in cleaned and ',' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            # Vietnamese/European: 1.500.000,00 -> 1500000.00
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US/UK: 1,500,000.00 -> 1500000.00
            cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        parts = cleaned.split('.')
        # If dot is used as thousand separator (e.g. 50.000, 1.000.000)
        if len(parts[-1]) == 3 or len(parts) > 2:
            cleaned = cleaned.replace('.', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts[-1]) == 3 or len(parts) > 2:
            cleaned = cleaned.replace(',', '')
        else:
            cleaned = cleaned.replace(',', '.')

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class InvoiceProcessor(ABC):
    def process_file(self, file_path, invoice_dict):
        try:
            file = PdfReader(file_path)
            all_text = []
            for page in file.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
            text = "\n".join(all_text)
        except Exception:
            raise InvoiceProcessingException()

        invoice_dict = self.generate_dict(text, invoice_dict)

        # Standardize amount
        if invoice_dict.get('value') is not None:
            invoice_dict['value'] = parse_amount(invoice_dict.get('value'))

        # Standardize date
        if invoice_dict.get('date') is not None:
            parsed = parse_date(invoice_dict.get('date'))
            invoice_dict['date'] = parsed if parsed else datetime.date.today()
        else:
            invoice_dict['date'] = datetime.date.today()

        if not invoice_dict.get('value') or invoice_dict.get('value') <= 0:
            raise InvoiceProcessingException()

        return invoice_dict

    @abstractmethod
    def generate_dict(self, text: str, invoice_dict: Dict):
        raise NotImplementedError()


class VietnameseInvoiceProcessor(InvoiceProcessor):
    """
    Parser thông minh dành cho hoá đơn / sao kê các ngân hàng Việt Nam:
    Vietcombank, Techcombank, MB Bank, MoMo, VietQR, v.v.
    """
    def generate_dict(self, text: str, invoice_dict: Dict):
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # 1. Tìm số tiền (Amount)
        # Các mẫu thường gặp: "Số tiền: 150.000 VND", "Số tiền giao dịch: 200,000 đ", "Số tiền thanh toán"
        amount_patterns = [
            r'(?:Số\s*tiền(?:\s*giao\s*dịch|\s*chuyển|\s*thanh\s*toán)?|Amount|Giá\s*trị|Tổng\s*tiền)\s*[:\-]?\s*([+\-]?\s*[\d.,]+\s*(?:VND|VNĐ|đ|Đ)?)',
            r'([+\-]?\s*[\d.,]+)\s*(?:VND|VNĐ|đ|Đ)',
        ]

        found_value = None
        for pattern in amount_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                found_value = m.group(1)
                break

        # Nếu không tìm thấy bằng regex toàn văn, quét từng dòng
        if not found_value:
            for i, line in enumerate(lines):
                if any(kw in line.lower() for kw in ['số tiền', 'amount', 'giá trị']):
                    # Kiểm tra xem số tiền có ở ngay trên cùng dòng không
                    val_match = re.search(r'([\d.,]+)', line)
                    if val_match:
                        found_value = val_match.group(1)
                        break
                    # Hoặc ở dòng kế tiếp
                    elif i + 1 < len(lines):
                        next_match = re.search(r'([\d.,]+)', lines[i + 1])
                        if next_match:
                            found_value = next_match.group(1)
                            break

        invoice_dict['value'] = found_value

        # 2. Tìm ngày tháng (Date)
        # Các mẫu thường gặp: "Thời gian: 10/10/2026 14:30:00", "Ngày thực hiện: 10-10-2026"
        date_pattern = r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}(?:\s*[-–]?\s*\d{1,2}:\d{1,2}(?::\d{1,2})?)?)'
        date_match = re.search(date_pattern, text)
        if date_match:
            invoice_dict['date'] = date_match.group(1)

        # 3. Tìm nội dung giao dịch / tiêu đề (Title)
        title_patterns = [
            r'(?:Nội\s*dung(?:\s*giao\s*dịch|\s*chuyển\s*tiền)?|Lời\s*nhắn|Ghi\s*chú|Details|Description)\s*[:\-]\s*([^\n\r]+)',
        ]
        for pattern in title_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                title = m.group(1).strip()
                if title:
                    invoice_dict['title'] = title[:50]
                break

        return invoice_dict


class SantanderInvoiceProcessor(InvoiceProcessor):
    def generate_dict(self, text, invoice_dict):
        chunks = text.split('\n')
        try:
            if 'Valor pago' in chunks:
                index_value = chunks.index('Valor pago')
                invoice_dict['value'] = chunks[index_value + 1]

            if 'Data e hora da transação' in chunks:
                index_date = chunks.index('Data e hora da transação')
                invoice_dict['date'] = chunks[index_date + 1]
        except ValueError:
            raise InvoiceProcessingException()

        return invoice_dict


class BancoDoBrasilInvoiceProcessor(InvoiceProcessor):
    def generate_dict(self, text, invoice_dict):
        chunks = text.split('\n')
        for chunk in chunks:
            parts = chunk.split()
            if parts and parts[0] == 'VALOR:':
                invoice_dict['value'] = parts[1].replace(',', '.')

            if parts and parts[0] == 'DATA:':
                invoice_dict['date'] = parts[1]

        return invoice_dict


class NubankInvoiceProcessor(InvoiceProcessor):
    def generate_dict(self, text, invoice_dict):
        # Fallback to general parsing
        return VietnameseInvoiceProcessor().generate_dict(text, invoice_dict)


class PDFInvoiceImporter:
    def __init__(self, file_path, institution):
        self.file_path = file_path
        self.invoice_dict = {'value': None, 'date': None, 'title': None}

        # Map Vietnamese & International institutions
        if institution in [
            'Ngân hàng Việt Nam (Chung / VietQR)',
            'Vietcombank',
            'Techcombank',
            'MB Bank',
            'MoMo',
        ]:
            self.processor = VietnameseInvoiceProcessor

        elif institution == 'Santander':
            self.processor = SantanderInvoiceProcessor

        elif institution == 'Banco do Brasil':
            self.processor = BancoDoBrasilInvoiceProcessor

        elif institution == 'Nubank':
            self.processor = NubankInvoiceProcessor

        else:
            # Fallback to general processor
            self.processor = VietnameseInvoiceProcessor

    def process_file(self):
        return self.processor().process_file(self.file_path, self.invoice_dict)
