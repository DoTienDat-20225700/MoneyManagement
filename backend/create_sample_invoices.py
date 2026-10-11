import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw
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

    # Test parser locally
    print("\n--- TEST PARSER LOCALLY (PDF & IMAGE RECEIPTS) ---")
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
