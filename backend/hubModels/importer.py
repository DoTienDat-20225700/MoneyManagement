import datetime
import json
import logging
import os
import re
from abc import abstractmethod, ABC
from typing import Dict, Optional, Tuple, List

from pypdf import PdfReader
from PIL import Image, ImageEnhance
import pytesseract
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    genai = None
    HAS_GEMINI = False


class InvoiceProcessingException(Exception):
    message = 'Không thể phân tích hoá đơn hoặc ảnh biên lai. Vui lòng kiểm tra lại ảnh chụp rõ nét hoặc chọn ngân hàng phù hợp.'


def is_image_file(file_path: str) -> bool:
    _, ext = os.path.splitext(file_path.lower())
    return ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff']


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
        "%H:%M:%S %d/%m/%Y",
        "%H:%M %d/%m/%Y",
        "%H:%M:%S %d-%m-%Y",
        "%H:%M %d-%m-%Y",
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
    # Remove currency words: VND, VNĐ, đ, Đ, R$, USD, dong, etc.
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


def extract_with_gemini(image_path: str, institution: Optional[str] = None) -> Optional[Dict]:
    """
    Sử dụng Gemini Vision API để bóc tách biên lai ảnh nếu đã cấu hình GEMINI_API_KEY.
    """
    api_key = ''
    try:
        if settings.configured:
            api_key = getattr(settings, 'GEMINI_API_KEY', '')
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or ''
    if not api_key or not HAS_GEMINI:
        return None

    try:
        genai.configure(api_key=api_key)
        img = Image.open(image_path)

        prompt = f"""Bạn là chuyên gia phân tích ảnh biên lai, hóa đơn chuyển khoản ngân hàng Việt Nam (Vietcombank, Techcombank, MB Bank, VietQR, MoMo, ZaloPay, BIDV, VPBank, Agribank, ACB, TPBank...).
Ngân hàng được chọn: {institution or 'Chung / VietQR'}.
Hãy trích xuất thông tin giao dịch từ ảnh này và trả về JSON chuẩn theo mẫu sau (KHÔNG kèm văn bản giải thích, KHÔNG bọc markdown):
{{
  "value": <số tiền chuyển/thanh toán kiểu số thực hoặc số nguyên, ví dụ: 250000>,
  "date": "<ngày giao dịch theo định dạng YYYY-MM-DD hoặc DD/MM/YYYY, ví dụ: 2026-10-11>",
  "title": "<nội dung giao dịch hoặc lời nhắn, tối đa 80 ký tự>",
  "recipient": "<tên người nhận/đơn vị thụ hưởng nếu có>"
}}
Nếu không tìm thấy trường nào, hãy đặt null. Luôn ưu tiên tìm chính xác số tiền và thời gian."""

        candidate_models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-pro-latest"]
        response = None
        for mod_name in candidate_models:
            try:
                model = genai.GenerativeModel(mod_name)
                response = model.generate_content([img, prompt])
                if response and response.text:
                    break
            except Exception as model_err:
                logger.info(f"Model {mod_name} not available: {model_err}")
                continue

        if not response or not response.text:
            return None

        raw_text = response.text.strip()
        if "```" in raw_text:
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_text)
            if match:
                raw_text = match.group(1).strip()

        data = json.loads(raw_text)
        if isinstance(data, dict):
            value = data.get('value')
            date_val = data.get('date')
            title = data.get('title')
            recipient = data.get('recipient')

            if not title and recipient:
                title = f"Chuyển tiền: {recipient}"
            elif recipient and title and recipient.lower() not in title.lower():
                title = f"{recipient} - {title}"

            return {
                'value': value,
                'date': date_val,
                'title': title[:100] if title else None
            }
    except Exception as e:
        logger.warning(f"Gemini Vision API extraction encountered an error: {e}. Falling back to OCR.")
        return None


def get_ocr_passes(image_path: str) -> List[str]:
    """
    Chạy OCR đa giai đoạn (Multi-pass OCR):
    - Giai đoạn 1: Ảnh gốc RGB (độ nét trung thực nhất cho font số)
    - Giai đoạn 2: Phóng to x2 mượt (LANCZOS) cho ảnh chụp kích thước nhỏ
    - Giai đoạn 3: Grayscale tăng tương phản nhẹ
    """
    results = []
    try:
        orig = Image.open(image_path)
        if orig.mode != 'RGB':
            orig = orig.convert('RGB')

        # Pass 1: Original RGB
        try:
            t1 = pytesseract.image_to_string(orig, lang='vie+eng')
            if t1 and t1.strip():
                results.append(t1)
        except Exception:
            pass

        # Pass 2: Upscaled x2 (nếu ảnh nhỏ hơn 1500px)
        w, h = orig.size
        if w < 1500:
            scale = 2.0 if w < 800 else 1.5
            up_img = orig.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            try:
                t2 = pytesseract.image_to_string(up_img, lang='vie+eng')
                if t2 and t2.strip():
                    results.append(t2)
            except Exception:
                pass

        # Pass 3: Grayscale
        gray = orig.convert('L')
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.4)
        try:
            t3 = pytesseract.image_to_string(enhanced, lang='vie+eng')
            if t3 and t3.strip():
                results.append(t3)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Failed to prepare OCR passes: {e}")

    return results


class InvoiceProcessor(ABC):
    def process_file(self, file_path, invoice_dict, institution=None):
        if is_image_file(file_path):
            # 1. Thử dùng Gemini Vision AI nếu có API Key
            gemini_result = extract_with_gemini(file_path, institution=institution)
            if gemini_result and (gemini_result.get('value') or gemini_result.get('date')):
                if gemini_result.get('value'):
                    invoice_dict['value'] = gemini_result.get('value')
                if gemini_result.get('date'):
                    invoice_dict['date'] = gemini_result.get('date')
                if gemini_result.get('title'):
                    invoice_dict['title'] = gemini_result.get('title')
            else:
                # 2. Fallback sang Tesseract Multi-pass OCR
                passes = get_ocr_passes(file_path)
                if not passes:
                    raise InvoiceProcessingException()

                found_valid = False
                for ocr_text in passes:
                    candidate_dict = self.generate_dict(ocr_text, dict(invoice_dict))
                    parsed_val = parse_amount(candidate_dict.get('value'))
                    if parsed_val > 0:
                        invoice_dict.update(candidate_dict)
                        found_valid = True
                        break

                if not found_valid:
                    # Thử lấy kết quả từ pass đầu tiên nếu có
                    invoice_dict = self.generate_dict(passes[0], invoice_dict)
        else:
            # File PDF
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

        # Chuẩn hoá số tiền
        if invoice_dict.get('value') is not None:
            invoice_dict['value'] = parse_amount(invoice_dict.get('value'))

        # Chuẩn hoá ngày giao dịch (nếu ảnh không có ngày thì lấy ngày hiện tại)
        if invoice_dict.get('date') is not None:
            parsed = parse_date(invoice_dict.get('date'))
            invoice_dict['date'] = parsed if parsed else datetime.date.today()
        else:
            invoice_dict['date'] = datetime.date.today()

        # Kiểm tra tính hợp lệ của số tiền
        if not invoice_dict.get('value') or invoice_dict.get('value') <= 0:
            raise InvoiceProcessingException()

        return invoice_dict

    @abstractmethod
    def generate_dict(self, text: str, invoice_dict: Dict):
        raise NotImplementedError()


class VietnameseInvoiceProcessor(InvoiceProcessor):
    """
    Parser thông minh dành cho hoá đơn PDF và ảnh chụp màn hình biên lai chuyển khoản:
    Vietcombank, Techcombank, MB Bank, MoMo, ZaloPay, VietQR, BIDV, VPBank, TPBank, ACB, v.v.
    """
    def generate_dict(self, text: str, invoice_dict: Dict):
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # 1. Tìm số tiền (Amount)
        amount_patterns = [
            # Dòng chứa từ khoá Số tiền / Amount
            r'(?:Số\s*tiền(?:\s*giao\s*dịch|\s*chuyển|\s*thanh\s*toán|\s*bằng\s*số)?|So\s*tien(?:\s*giao\s*dich|\s*chuyen|\s*thanh\s*toan)?|Amount|Giá\s*trị|Gia\s*tri|Tổng\s*tiền|Tong\s*tien)\s*[:\-]?\s*([+\-]?\s*[\d.,]+\s*(?:VND|VNĐ|đ|Đ)?)',
            # Dòng chứa số tiền kèm đơn vị VND / đ
            r'([+\-]?\s*[\d.,]{3,})\s*(?:VND|VNĐ|đ|Đ|dong|đồng)',
        ]

        found_value = None
        for pattern in amount_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                found_value = m.group(1)
                break

        # Nếu chưa tìm thấy, quét từng dòng tìm từ khoá và số tiền đi kèm hoặc ở dòng kế tiếp
        if not found_value:
            for i, line in enumerate(lines):
                lower_line = line.lower()
                if any(kw in lower_line for kw in ['số tiền', 'so tien', 'amount', 'giá trị', 'gia tri', 'tổng tiền', 'tong tien']):
                    val_match = re.search(r'([\d.,]{3,})', line)
                    if val_match:
                        found_value = val_match.group(1)
                        break
                    elif i + 1 < len(lines):
                        next_match = re.search(r'([\d.,]{3,})', lines[i + 1])
                        if next_match:
                            found_value = next_match.group(1)
                            break

        # Nếu vẫn chưa tìm thấy, tìm dòng đứng độc lập chỉ chứa số tiền (ví dụ trong app MB, Techcombank: 500,000 VND)
        if not found_value:
            for line in lines:
                m_standalone = re.search(r'^[+\-]?\s*([\d.,]{4,})\s*(?:VND|VNĐ|đ|Đ)?$', line.strip(), re.IGNORECASE)
                if m_standalone:
                    found_value = m_standalone.group(1)
                    break

        invoice_dict['value'] = found_value

        # 2. Tìm ngày tháng (Date)
        date_patterns = [
            r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{4}(?:\s*[-–,\s]+\d{1,2}:\d{1,2}(?::\d{1,2})?)?)',
            r'(\d{1,2}:\d{1,2}(?::\d{1,2})?\s*[-–,\s]+\d{1,2}[/.-]\d{1,2}[/.-]\d{4})',
            r'(\d{4}[/.-]\d{1,2}[/.-]\d{1,2})',
        ]
        for dp in date_patterns:
            date_match = re.search(dp, text)
            if date_match:
                invoice_dict['date'] = date_match.group(1)
                break

        # 3. Tìm người nhận & nội dung giao dịch (Recipient & Content)
        recipient = None
        recipient_patterns = [
            r'(?:Người\s*nh[aâã][nr]|Nguoi\s*nh[aâã][nr]|Ngu[oõôơ]i\s*nh[aâã][nr]|Người\s*thụ\s*hưởng|Nguoi\s*thu\s*huong|Tên\s*người\s*nh[aâã][nr]|Ten\s*nguoi\s*nh[aâã][nr]|Tài\s*khoản\s*nh[aâã][nr]|Tai\s*khoan\s*nh[aâã][nr]|Đến\s*tài\s*khoản|Den\s*tai\s*khoan|Beneficiary|To)\s*[:\-\s]\s*([^\n\r]+)',
        ]
        ignored_keywords = [
            'sotien', 'satien', 'thoigian', 'magiaodich', 'trangthai',
            'nganhang', 'sotaikhoan', 'sodu', 'luuanh', 'luumau', 'chiase',
            'dichvu', 'madonhang', 'chuyentien', 'giaodich', 'vnd', 'vcb', 'tcb'
        ]

        for pattern in recipient_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                clean_rec = m.group(1).strip().strip("':-\"’`,")
                no_space = re.sub(r'[\s:.\-]+', '', clean_rec.lower())
                if clean_rec and len(clean_rec) >= 2 and not any(kw in no_space for kw in ignored_keywords):
                    recipient = clean_rec
                    break

        content = None
        content_patterns = [
            r'(?:Nội\s*dung(?:\s*giao\s*dịch|\s*chuyển\s*tiền|\s*thanh\s*toán)?|Noi\s*dung(?:\s*giao\s*dich|\s*chuyen\s*tien|\s*thanh\s*toan)?|N[oôg]i\s*dung|Lời\s*nhắn|Loi\s*nhan|Ghi\s*chú|Ghi\s*chu|Details|Description|Message)\s*[:\-\s]\s*([^\n\r]+)',
        ]
        for pattern in content_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                clean_cnt = m.group(1).strip().strip("':-\"’`,")
                no_space = re.sub(r'[\s:.\-]+', '', clean_cnt.lower())
                if clean_cnt and len(clean_cnt) >= 2 and not any(kw in no_space for kw in ignored_keywords):
                    content = clean_cnt
                    break

        # 4. Trích xuất thông minh cho ảnh chụp app ngân hàng không có nhãn rõ ràng
        if not recipient or not content:
            system_terms = [
                'thành công', 'thanh cong', 'giao dịch', 'giao dich',
                'lưu ảnh', 'luu anh', 'lưu mẫu', 'luu mau', 'chia sẻ', 'chia se',
                'cảm ơn', 'cam on', 'mbbank', 'mbbonk', 'vietcombank', 'techcombank',
                'vietinbank', 'bidv', 'vpbank', 'agribank', 'tpbank', 'vnd', 'vnđ', 'vcb', 'tcb'
            ]
            candidates = []
            for line in lines:
                low = line.lower()
                # Bỏ qua dòng số tiền
                if re.search(r'[\d.,]+\s*(?:vnd|vnđ|đ)', low) or re.match(r'^[+\-]?\s*[\d.,\s]+$', line):
                    continue
                # Bỏ qua dòng trạng thái / nút bấm hệ thống
                if any(term in low for term in system_terms) and 'chuyen tien' not in low and 'chuyển tiền' not in low and 'thanh toan' not in low:
                    continue
                cleaned_line = re.sub(r'[^a-zA-Z0-9\sÀ-ỹ]', '', line).strip()
                if len(cleaned_line) >= 4 and not cleaned_line.isdigit():
                    candidates.append(line.strip())

            for c in candidates:
                letters = [ch for ch in c if ch.isalpha()]
                upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters) if letters else 0
                if upper_ratio > 0.75 and not recipient:
                    recipient = c
                elif not content and (any(kw in c.lower() for kw in ['chuyen tien', 'chuyển tiền', 'thanh toan', 'thanh toán']) or len(c) > 6):
                    content = c

        # Tổng hợp title
        if recipient and content and recipient.lower() != content.lower():
            invoice_dict['title'] = f"{recipient} - {content}"[:100]
        elif content:
            invoice_dict['title'] = content[:100]
        elif recipient:
            invoice_dict['title'] = f"Chuyển tiền: {recipient}"[:100]

        return invoice_dict


class InvoiceImporter:
    """
    Importer đa năng hỗ trợ cả tệp PDF hoá đơn và ảnh chụp màn hình biên lai chuyển khoản
    (VietQR, app ngân hàng, ví điện tử).
    """
    def __init__(self, file_path, institution=None):
        self.file_path = file_path
        self.institution = institution or 'Ngân hàng Việt Nam (Chung / VietQR)'
        self.invoice_dict = {'value': None, 'date': None, 'title': None}
        self.processor = VietnameseInvoiceProcessor

    def process_file(self):
        result = self.processor().process_file(self.file_path, self.invoice_dict, institution=self.institution)
        # Nếu chưa trích xuất được tiêu đề cụ thể, đặt tiêu đề mặc định theo ngân hàng
        if not result.get('title'):
            if self.institution and self.institution != 'Ngân hàng Việt Nam (Chung / VietQR)':
                result['title'] = f"Giao dịch {self.institution}"
            else:
                result['title'] = "Giao dịch chuyển khoản"
        return result


# Alias để giữ tương thích ngược
PDFInvoiceImporter = InvoiceImporter
