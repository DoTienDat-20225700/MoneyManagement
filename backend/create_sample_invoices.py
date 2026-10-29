import os
import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from hubModels.importer import InvoiceImporter

def create_sample_pdf(file_path, bank_name, details):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 60, f"BIEN LAI GIAO DICH - {bank_name.upper()}")

    c.setStrokeColorRGB(0.2, 0.6, 0.3)
    c.setLineWidth(2)
    c.line(50, height - 70, width - 50, height - 70)

    # Details
    c.setFont("Helvetica", 12)
    y = height - 120
    for label, val in details:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, y, f"{label}:")
        c.setFont("Helvetica", 12)
        c.drawString(220, y, str(val))
        y -= 35

    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(1)
    c.line(50, y - 20, width - 50, y - 20)

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y - 40, "Cam on quy khach da su dung dich vu cua chung toi.")
    c.save()
    print(f"Created PDF: {file_path}")

def create_sample_image(file_path, bank_name, amount, recipient, content, date_str, header_color="#0f5132"):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    img = Image.new("RGB", (720, 960), color="#f8f9fa")
    draw = ImageDraw.Draw(img)

    # Top Brand Bar
    draw.rectangle([(0, 0), (720, 110)], fill=header_color)
    draw.text((45, 42), bank_name.upper(), fill="#ffffff")

    # Status Pill
    draw.rectangle([(210, 140), (510, 185)], fill="#d1e7dd")
    draw.text((230, 153), "GIAO DICH THANH CONG", fill="#0f5132")

    # Amount Display
    draw.text((220, 220), f"{amount} VND", fill="#111111")

    # Card Box
    draw.rectangle([(40, 290), (680, 870)], fill="#ffffff", outline="#dee2e6", width=2)

    rows = [
        ("Ngan hang", bank_name),
        ("Thoi gian giao dich", date_str),
        ("Nguoi nhan", recipient),
        ("So tien", f"{amount} VND"),
        ("Noi dung", content),
        ("Ma giao dich", "VN" + "".join([c for c in str(abs(hash(file_path)))[:10]])),
        ("Trang thai", "Thanh cong"),
    ]

    y = 320
    for label, val in rows:
        draw.text((70, y), f"{label}:", fill="#6c757d")
        draw.text((270, y), str(val), fill="#212529")
        draw.line([(70, y + 50), (650, y + 50)], fill="#f1f3f5", width=1)
        y += 75

    img.save(file_path)
    print(f"Created Image: {file_path}")


# -------------------------------------------------------------
# BENCHMARK SUITE GENERATION (24 Diverse Invoices & Receipts)
# -------------------------------------------------------------

def get_benchmark_font(size: int, bold: bool = False):
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "DejaVuSans.ttf",
    ]
    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_benchmark_pdf(file_path, bank_name, amount, recipient, content, date_str, header_color=(0.1, 0.4, 0.2)):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 60, f"BIEN LAI GIAO DICH - {bank_name.upper()}")

    c.setStrokeColorRGB(*header_color)
    c.setLineWidth(2)
    c.line(50, height - 70, width - 50, height - 70)

    formatted_amount = f"{int(amount):,} VND".replace(",", ".")
    details = [
        ("Ngan hang", bank_name),
        ("Ma giao dich", "VN" + "".join([ch for ch in str(abs(hash(file_path)))[:10]])),
        ("Ngay giao dich", date_str),
        ("So tien giao dich", formatted_amount),
        ("Nguoi nhan", recipient),
        ("Noi dung chuyen tien", content),
        ("Trang thai", "Giao dich thanh cong"),
    ]

    # Details
    c.setFont("Helvetica", 12)
    y = height - 120
    for label, val in details:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, y, f"{label}:")
        c.setFont("Helvetica", 12)
        c.drawString(220, y, str(val))
        y -= 35

    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(1)
    c.line(50, y - 20, width - 50, y - 20)

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y - 40, "Cam on quy khach da su dung dich vu cua chung toi.")
    c.save()
    print(f"Created Benchmark PDF: {file_path}")


def create_benchmark_image(file_path, bank_name, amount, recipient, content, date_str, header_color="#0f5132", condition="image_standard"):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    img = Image.new("RGB", (720, 960), color="#f8f9fa")
    draw = ImageDraw.Draw(img)

    font_header = get_benchmark_font(28, bold=True)
    font_pill = get_benchmark_font(18, bold=True)
    font_amount = get_benchmark_font(34, bold=True)
    font_label = get_benchmark_font(18, bold=True)
    font_val = get_benchmark_font(18, bold=False)

    # Top Brand Bar
    draw.rectangle([(0, 0), (720, 110)], fill=header_color)
    draw.text((45, 38), bank_name.upper(), fill="#ffffff", font=font_header)

    # Status Pill
    draw.rectangle([(180, 140), (540, 190)], fill="#d1e7dd")
    draw.text((215, 153), "GIAO DICH THANH CONG", fill="#0f5132", font=font_pill)

    # Amount Display
    formatted_amount = f"{int(amount):,} VND".replace(",", ".")
    draw.text((220, 220), formatted_amount, fill="#111111", font=font_amount)

    # Card Box
    draw.rectangle([(40, 280), (680, 890)], fill="#ffffff", outline="#dee2e6", width=2)

    rows = [
        ("Ngan hang", bank_name),
        ("Thoi gian giao dich", date_str),
        ("Nguoi nhan", recipient),
        ("So tien", f"{formatted_amount}"),
        ("Noi dung", content),
        ("Ma giao dich", "VN" + "".join([c for c in str(abs(hash(file_path)))[:10]])),
        ("Trang thai", "Thanh cong"),
    ]

    y = 310
    for label, val in rows:
        draw.text((70, y), f"{label}:", fill="#495057", font=font_label)
        draw.text((270, y), str(val), fill="#212529", font=font_val)
        draw.line([(70, y + 55), (650, y + 55)], fill="#e9ecef", width=1)
        y += 80

    if condition == "image_small_scale":
        # Downscale to width 400 (< 800px) so LANCZOS upscale pass is tested
        img = img.resize((400, 533), Image.Resampling.LANCZOS)
    elif condition == "image_low_contrast":
        # Reduce contrast so Pass 3 contrast enhancement is tested
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(0.65)

    img.save(file_path)
    print(f"Created Benchmark Image [{condition}]: {file_path}")


def create_benchmark_suite(benchmark_dir):
    """
    Sinh 24 file benchmark kiểm thử đa dạng cho 6 đơn vị tài chính / ngân hàng:
    - Vietcombank, Techcombank, MB Bank, BIDV, MoMo, VietQR
    Mỗi đơn vị có 4 biến thể:
    1. pdf_digital (Hóa đơn PDF điện tử)
    2. image_standard (Ảnh biên lai rõ nét chuẩn)
    3. image_small_scale (Ảnh kích thước nhỏ cần upscale LANCZOS)
    4. image_low_contrast (Ảnh mờ / tương phản thấp)
    """
    os.makedirs(benchmark_dir, exist_ok=True)

    institutions = [
        {
            "key": "vietcombank",
            "name": "Vietcombank",
            "color": "#005a36",
            "pdf_color": (0.0, 0.35, 0.21),
            "amount": 500000.0,
            "date_str": "12/10/2026 09:15:00",
            "expected_date": "2026-10-12",
            "recipient": "CONG TY DIEN LUC HA NOI",
            "content": "Thanh toan tien dien thang 10",
            "keywords": ["dien luc", "tien dien"],
        },
        {
            "key": "techcombank",
            "name": "Techcombank",
            "color": "#e71d28",
            "pdf_color": (0.9, 0.11, 0.15),
            "amount": 1250000.0,
            "date_str": "14/10/2026 14:30:00",
            "expected_date": "2026-10-14",
            "recipient": "CONG TY CP BACH HOA XANH",
            "content": "Mua sam thuc pham gia dinh",
            "keywords": ["bach hoa xanh", "thuc pham"],
        },
        {
            "key": "mbbank",
            "name": "MB Bank",
            "color": "#103680",
            "pdf_color": (0.06, 0.21, 0.5),
            "amount": 2450000.0,
            "date_str": "15/10/2026 10:20:00",
            "expected_date": "2026-10-15",
            "recipient": "VIETNAM AIRLINES JSC",
            "content": "Ve may bay khu hoi Ha Noi Da Nang",
            "keywords": ["vietnam airlines", "may bay"],
        },
        {
            "key": "bidv",
            "name": "BIDV",
            "color": "#004838",
            "pdf_color": (0.0, 0.28, 0.22),
            "amount": 3800000.0,
            "date_str": "16/10/2026 11:45:00",
            "expected_date": "2026-10-16",
            "recipient": "TRUONG DAI HOC BACH KHOA",
            "content": "Nop hoc phi ky 1 nam hoc 2026",
            "keywords": ["bach khoa", "hoc phi"],
        },
        {
            "key": "momo",
            "name": "Ví MoMo",
            "color": "#a50064",
            "pdf_color": (0.64, 0.0, 0.39),
            "amount": 85000.0,
            "date_str": "17/10/2026 12:10:00",
            "expected_date": "2026-10-17",
            "recipient": "HIGHLANDS COFFEE",
            "content": "Thanh toan 2 ly ca phe Highlands",
            "keywords": ["highlands", "ca phe"],
        },
        {
            "key": "vietqr",
            "name": "VietQR",
            "color": "#003b73",
            "pdf_color": (0.0, 0.23, 0.45),
            "amount": 420000.0,
            "date_str": "18/10/2026 16:05:00",
            "expected_date": "2026-10-18",
            "recipient": "NHA THUOC PHARMACITY",
            "content": "Mua thuoc va vat tu y te gia dinh",
            "keywords": ["pharmacity", "thuoc"],
        },
    ]

    ground_truth = []

    for inst in institutions:
        key = inst["key"]

        # 1. PDF Digital
        pdf_name = f"bm_{key}_digital.pdf"
        pdf_path = os.path.join(benchmark_dir, pdf_name)
        create_benchmark_pdf(
            pdf_path,
            bank_name=inst["name"],
            amount=inst["amount"],
            recipient=inst["recipient"],
            content=inst["content"],
            date_str=inst["date_str"],
            header_color=inst["pdf_color"]
        )
        ground_truth.append({
            "file_name": pdf_name,
            "expected_value": inst["amount"],
            "expected_date": inst["expected_date"],
            "expected_title_keywords": inst["keywords"],
            "condition": "pdf_digital"
        })

        # 2. Image Standard (720x960)
        img_std_name = f"bm_{key}_standard.png"
        img_std_path = os.path.join(benchmark_dir, img_std_name)
        create_benchmark_image(
            img_std_path,
            bank_name=inst["name"],
            amount=inst["amount"],
            recipient=inst["recipient"],
            content=inst["content"],
            date_str=inst["date_str"],
            header_color=inst["color"],
            condition="image_standard"
        )
        ground_truth.append({
            "file_name": img_std_name,
            "expected_value": inst["amount"],
            "expected_date": inst["expected_date"],
            "expected_title_keywords": inst["keywords"],
            "condition": "image_standard"
        })

        # 3. Image Small Scale (400x533, Lanczos required)
        img_small_name = f"bm_{key}_small.png"
        img_small_path = os.path.join(benchmark_dir, img_small_name)
        create_benchmark_image(
            img_small_path,
            bank_name=inst["name"],
            amount=inst["amount"],
            recipient=inst["recipient"],
            content=inst["content"],
            date_str=inst["date_str"],
            header_color=inst["color"],
            condition="image_small_scale"
        )
        ground_truth.append({
            "file_name": img_small_name,
            "expected_value": inst["amount"],
            "expected_date": inst["expected_date"],
            "expected_title_keywords": inst["keywords"],
            "condition": "image_small_scale"
        })

        # 4. Image Low Contrast
        img_low_name = f"bm_{key}_low_contrast.png"
        img_low_path = os.path.join(benchmark_dir, img_low_name)
        create_benchmark_image(
            img_low_path,
            bank_name=inst["name"],
            amount=inst["amount"],
            recipient=inst["recipient"],
            content=inst["content"],
            date_str=inst["date_str"],
            header_color=inst["color"],
            condition="image_low_contrast"
        )
        ground_truth.append({
            "file_name": img_low_name,
            "expected_value": inst["amount"],
            "expected_date": inst["expected_date"],
            "expected_title_keywords": inst["keywords"],
            "condition": "image_low_contrast"
        })

    # Export ground_truth.json
    gt_path = os.path.join(benchmark_dir, "ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Đã xuất ground truth benchmark ({len(ground_truth)} mẫu): {gt_path}")
    return ground_truth


def main():
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../sample_invoices"))
    os.makedirs(target_dir, exist_ok=True)

    # 1. Vietcombank PDF
    vcb_pdf = os.path.join(target_dir, "hoa_don_vietcombank.pdf")
    create_sample_pdf(vcb_pdf, "Vietcombank", [
        ("Ngan hang", "Ngan hang TMCP Ngoai thuong Viet Nam (Vietcombank)"),
        ("Ma giao dich", "VCB98234710293"),
        ("Thoi gian", "11/10/2026 09:30:15"),
        ("So tien", "500,000 VND"),
        ("Noi dung", "Thanh toan tien dien thang 10"),
        ("Trang thai", "Giao dich thanh cong"),
    ])

    # 2. Techcombank PDF
    tcb_pdf = os.path.join(target_dir, "hoa_don_techcombank.pdf")
    create_sample_pdf(tcb_pdf, "Techcombank", [
        ("Ngan hang", "Techcombank"),
        ("Ma giao dich", "TCB874920173"),
        ("Ngay giao dich", "10/10/2026 14:15:00"),
        ("So tien giao dich", "1,250,000 VND"),
        ("Noi dung chuyen tien", "Mua sam do gia dung sieu thi"),
        ("Trang thai", "Thanh cong"),
    ])

    # 3. MoMo PDF
    momo_pdf = os.path.join(target_dir, "hoa_don_momo.pdf")
    create_sample_pdf(momo_pdf, "Vi MoMo", [
        ("Dich vu", "Vi dien tu MoMo"),
        ("Ma don hang", "MOMO-9912048"),
        ("Thoi gian thanh toan", "11/10/2026 11:20:00"),
        ("So tien thanh toan", "65,000 VND"),
        ("Loi nhan", "Thanh toan ca phe Highlands"),
        ("Ket qua", "Thanh cong"),
    ])

    # 4. VietQR / MB Bank Image Receipt
    vietqr_img = os.path.join(target_dir, "bien_lai_vietqr.png")
    create_sample_image(
        vietqr_img,
        bank_name="VietQR / MB Bank",
        amount="350,000",
        recipient="NGUYEN VAN A",
        content="Chuyen tien mua sach vo",
        date_str="11/10/2026 15:30:00",
        header_color="#003b73"
    )

    # 5. Vietcombank Image Receipt
    vcb_img = os.path.join(target_dir, "bien_lai_vietcombank.png")
    create_sample_image(
        vcb_img,
        bank_name="Vietcombank",
        amount="850,000",
        recipient="TRAN THI B",
        content="Thanh toan tien phong tro thang 10",
        date_str="11/10/2026 10:15:20",
        header_color="#005a36"
    )

    # 6. MoMo Image Receipt
    momo_img = os.path.join(target_dir, "bien_lai_momo.png")
    create_sample_image(
        momo_img,
        bank_name="Vi MoMo",
        amount="120,000",
        recipient="NHA HANG PHO 24",
        content="Thanh toan an trua",
        date_str="11/10/2026 12:45:00",
        header_color="#a50064"
    )

    # Sinh bộ 24 mẫu benchmark chuyên sâu
    benchmark_dir = os.path.join(target_dir, "benchmark")
    create_benchmark_suite(benchmark_dir)

    # Test parser locally với 6 mẫu cơ bản
    print("\n--- TEST PARSER LOCALLY (6 SAMPLE INVOICES) ---")
    test_cases = [
        (vcb_pdf, "Vietcombank"),
        (tcb_pdf, "Techcombank"),
        (momo_pdf, "Ví điện tử MoMo"),
        (vietqr_img, "Ngân hàng Việt Nam (Chung / VietQR)"),
        (vcb_img, "Vietcombank"),
        (momo_img, "Ví điện tử MoMo"),
    ]
    for path, inst in test_cases:
        res = InvoiceImporter(path, inst).process_file()
        print(f"[{os.path.basename(path)}] ({inst}) -> Title: '{res.get('title')}', Amount: {res.get('value'):,.0f} VND, Date: {res.get('date')}")

if __name__ == "__main__":
    main()
