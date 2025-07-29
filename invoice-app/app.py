from io import BytesIO
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import os, json, urllib.parse

from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image
from num2words import num2words

# ---------- config  -------------------------------------------------
APP = Flask(__name__)

# MySQL Configuration with URL-encoded password
password = urllib.parse.quote_plus("Koti@6102")
APP.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://root:{password}@localhost/invoice_db'
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(APP)

COMPANY = {
    "name":  "SATYA SAI BABA AUTO ELECTRICAL WORKS",
    "tag":   "Authorised MICO BOSCH Service",
    "addr1": "Venkateswara Theatre Rd, Near IMA Hall, Ganga Enclave",
    "addr2": "Satyanarayana Puram, GUDIVADA – 521 301",
    "state": "Andhra Pradesh · State Code : 37",
    "phone": "9958592564 , 8074546541",
    "gstin": "GSTIN : 37CYCP5977H1ZM",
    "logo":  os.path.join("static", "logo.png")
}

CGST = SGST = Decimal("9")  # %

def money(val: Decimal) -> str:
    return f"{val.quantize(Decimal('0.01'), ROUND_HALF_UP)}"

# simple counter (for demo; in prod use DB/Redis)
CURRENT_INV = {"no": 1}

# ---------- routes  -------------------------------------------------
@APP.route("/")
def index():
    return render_template("index.html",
                           company=COMPANY,
                           inv_no=f"{CURRENT_INV['no']:04}",
                           today=datetime.now().strftime("%d-%m-%Y"))

@APP.post("/generate")
def generate():
    data = json.loads(request.form["payload"])   # payload = JSON string
    items     = data["items"]
    cust      = data["customer"]
    with_gst  = data.get("with_gst", True)

    # choose rates
    cgst_rate = CGST if with_gst else Decimal("0")
    sgst_rate = SGST if with_gst else Decimal("0")

    inv_no = f"{CURRENT_INV['no']:04}"
    CURRENT_INV["no"] += 1                       # increment counter

    # Calculate totals
    subtotal = Decimal("0")
    for item in items:
        item['amount'] = Decimal(item['rate']) * Decimal(item['qty'])
        subtotal += item['amount']
    
    cgst = (subtotal * cgst_rate / 100).quantize(Decimal('0.01'))
    sgst = (subtotal * sgst_rate / 100).quantize(Decimal('0.01'))
    total = subtotal + cgst + sgst

    # Save to database
    try:
        # Create or find customer
        customer = Customer.query.filter_by(phone=cust.get('phone')).first()
        if not customer:
            customer = Customer(
                name=cust.get('name', ''),
                phone=cust.get('phone', ''),
                address=cust.get('address', ''),
                location=f"{cust.get('district', '')}, {cust.get('state', '')}".strip(', '),
                vehicle_no=cust.get('vehicle', '')
            )
            db.session.add(customer)
            db.session.flush()  # Get the customer ID
        else:
            # Update existing customer details if needed
            customer.name = cust.get('name', customer.name)
            customer.address = cust.get('address', customer.address)
            customer.location = f"{cust.get('district', '')}, {cust.get('state', '')}".strip(', ')
            customer.vehicle_no = cust.get('vehicle', customer.vehicle_no)
            db.session.flush()
        
        # Create invoice
        invoice = Invoice(
            invoice_no=inv_no,
            date=datetime.now().date(),
            customer_id=customer.id,
            subtotal=subtotal,
            cgst=cgst,
            sgst=sgst,
            total=total
        )
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID
        
        # Add invoice items
        for item in items:
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                description=item['desc'],
                quantity=item['qty'],
                rate=Decimal(item['rate']),
                amount=Decimal(item['amount'])
            )
            db.session.add(invoice_item)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving to database: {str(e)}")
        return {"error": "Failed to save invoice to database"}, 500

    # ----- build PDF in memory -------------------------------------
    buf = BytesIO()
    c   = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    
    # Import additional ReportLab modules for better styling
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    
    # Define colors - professional color scheme
    primary_color = colors.HexColor('#2c3e50')  # Dark blue-gray
    secondary_color = colors.HexColor('#7f8c8d')  # Gray
    accent_color = colors.HexColor('#3498db')  # Blue
    
    # Page margins for better structure
    margin = 30
    content_width = w - (2 * margin)
    
    # Current Y position tracker
    current_y = h - margin - 20
    
    # ===== PAGE BORDER =====
    c.setStrokeColor(primary_color)
    # Use a single, clean border with padding
    c.setLineWidth(1.5)
    border_padding = 10
    c.rect(
        margin - border_padding,
        margin - border_padding,
        w - 2 * (margin - border_padding),
        h - 2 * (margin - border_padding)
    )

    # ===== HEADER SECTION =====
    header_height = 100
    # Remove header border, just use background color
    c.setFillColor(colors.HexColor('#f8f9fa'))
    c.rect(margin, current_y - header_height, content_width, header_height, fill=1, stroke=0)
    c.setFillColor(colors.black)
    
    # Calculate total amount first
    tot_amt = tot_cg = tot_sg = Decimal("0.00")
    for item in items:
        qty = Decimal(item["qty"] or "0")
        rate = Decimal(item["rate"] or "0")
        amt = qty * rate
        
        if with_gst:
            cg = (amt * cgst_rate) / 100
            sg = (amt * sgst_rate) / 100
            tot_cg += cg
            tot_sg += sg
            amt += cg + sg
            
        tot_amt += amt
    
    # Format shop details for the QR code to be easily readable when scanned
    shop_details_for_qr = (
        f"Shop Name: {COMPANY['name']}\n"
        f"Address: {COMPANY['addr1']}, {COMPANY['addr2']}\n"
        f"Phone: {COMPANY['phone']}\n"
        f"GSTIN: {COMPANY['gstin'].replace('GSTIN : ', '')}"
    )
    
    # Now generate QR code with the shop details
    qr = qrcode.make(shop_details_for_qr, box_size=3, border=1)
    qr_buf = BytesIO()
    qr.save(qr_buf)
    qr_buf.seek(0)
    
    # QR Code positioning in header (top right corner)
    qr_size = 60
    qr_x = w - margin - qr_size - 10
    qr_y = current_y - qr_size - 10
    c.drawImage(ImageReader(qr_buf), qr_x, qr_y, qr_size, qr_size)
    
    # QR label
    c.setFont("Helvetica", 7)
    c.drawCentredString(qr_x + qr_size/2, qr_y - 8, "Scan for Verification")
    
    # Company name - centered but adjusted for QR code space
    company_text_width = content_width - qr_size - 20  # Leave space for QR
    company_center_x = margin + (company_text_width / 2)
    
    # Company name - centered and bold
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(company_center_x, current_y - 25, COMPANY["name"])
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(company_center_x, current_y - 40, COMPANY["tag"])
    
    # Address lines
    c.setFont("Helvetica", 10)
    c.drawCentredString(company_center_x, current_y - 57, COMPANY["addr1"])
    c.drawCentredString(company_center_x, current_y - 69, f"{COMPANY['addr2']}, {COMPANY['state']}")
    
    # Contact info
    c.setFont("Helvetica", 9)
    contact_text = f"Cell: {COMPANY['phone']} | {COMPANY['gstin']}"
    c.drawCentredString(company_center_x, current_y - 84, contact_text)
    
    current_y -= header_height + 10
    
    # ===== CUSTOMER AND INVOICE INFO SECTION =====
    info_height = 90  # Slightly taller for better spacing
    
    # Left side - Customer info (60% width)
    customer_width = content_width * 0.6
    # Remove customer box border
    c.setFillColor(colors.HexColor('#f8f9fa'))
    c.rect(margin, current_y - info_height, customer_width, info_height, fill=1, stroke=0)
    c.setFillColor(colors.black)
    
    # Customer details (left side)
    customer_y = current_y - 20
    # Make "Bill To:" heading larger and bolder
    c.setFont("Helvetica-Bold", 14)
    heading_x = margin + (customer_width / 2)
    c.drawCentredString(heading_x, customer_y, "Bill To")

    # Details to display, excluding the ones to be placed side-by-side
    details_x = margin + 10
    details_y = customer_y - 15 # Add space below heading

    # Combine District and State
    location = f"{cust.get('district', '')}, {cust.get('state', '')}".strip(', ')

    customer_details = [
        ("Name", cust.get('name', '')),
        ("Address", cust.get('address', '')),
        ("Phone", cust.get('phone', ''))
    ]

    # Calculate alignment based on all labels to ensure consistency
    align_labels = [label for label, _ in customer_details] + ["Location", "Vehicle No"]
    max_label_width = max(c.stringWidth(f"{label}:", "Helvetica-Bold", 10) for label in align_labels)
    value_x = details_x + max_label_width + 5

    # Draw the main details
    for i, (label, value) in enumerate(customer_details):
        y_pos = details_y - (15 * i)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(details_x, y_pos, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(value_x, y_pos, value)

    # Draw Location and Vehicle No on the same line
    y_pos = details_y - (15 * len(customer_details))
    
    # --- Draw Location ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(details_x, y_pos, "Location:")
    c.setFont("Helvetica", 10)
    c.drawString(value_x, y_pos, location)

    # --- Draw Vehicle No ---
    # Position it after the location text
    location_width = c.stringWidth(location, "Helvetica", 10)
    vehicle_x_start = value_x + location_width + 20 # Add padding

    c.setFont("Helvetica-Bold", 10)
    c.drawString(vehicle_x_start, y_pos, "Vehicle No:")
    c.setFont("Helvetica", 10)
    vehicle_label_width = c.stringWidth("Vehicle No:", "Helvetica-Bold", 10)
    c.drawString(vehicle_x_start + vehicle_label_width + 5, y_pos, cust.get('vehicle', ''))

    # Right side - Invoice info (40% width)
    invoice_width = content_width * 0.35
    invoice_x = w - margin - invoice_width
    # Remove invoice box border, just use subtle background
    c.setFillColor(colors.HexColor('#f8f9fa'))
    c.rect(invoice_x, current_y - info_height, invoice_width, info_height, fill=1, stroke=0)
    c.setFillColor(colors.black)
    
    # Invoice header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(invoice_x + (w - margin - invoice_x)/2, current_y - 20, "TAX INVOICE")
    
    # --- Invoice Details (Right-aligned) ---
    details_x_label = invoice_x + 10
    details_x_value = w - margin - 10 # Right edge of the box

    c.setFont("Helvetica-Bold", 10)
    c.drawString(details_x_label, current_y - 40, "Invoice No:")
    c.drawString(details_x_label, current_y - 55, "Date:")
    c.drawString(details_x_label, current_y - 70, "Job Card No:")

    c.setFont("Helvetica", 10)
    c.drawRightString(details_x_value, current_y - 40, inv_no)
    c.drawRightString(details_x_value, current_y - 55, datetime.now().strftime("%d-%m-%Y"))
    c.drawRightString(details_x_value, current_y - 70, cust.get("jobcard") or "N/A")
    
    # Add a small gap between sections
    current_y -= info_height + 20
    
    # ===== ITEMS TABLE =====
    # Define table headers and column widths based on GST status
    if with_gst:
        table_headers = ["S.No", "PARTICULARS", "HSN", "Qty", "Rate", "Taxable Amt", "CGST 9%", "SGST 9%", "Amount"]
        col_widths = [30, 120, 55, 35, 60, 60, 55, 55, 65] # Adjusted to fit page
    else:
        table_headers = ["S.No", "PARTICULARS", "HSN", "Qty", "Rate", "Amount"]
        col_widths = [30, 220, 70, 40, 70, 70]

    # Table data
    table_data = [table_headers]
    
    s_no = 1
    for item in items:
        qty = Decimal(item.get("qty", 0) or "0")
        rate = Decimal(item.get("rate", 0) or "0")
        taxable_amt = qty * rate
        
        if with_gst:
            cgst_val = (taxable_amt * cgst_rate) / 100
            sgst_val = (taxable_amt * sgst_rate) / 100
            amt = taxable_amt + cgst_val + sgst_val
            row = [s_no, item["desc"], item["hsn"], qty, money(rate), money(taxable_amt), money(cgst_val), money(sgst_val), money(amt)]
        else:
            amt = taxable_amt
            row = [s_no, item["desc"], item["hsn"], qty, money(rate), money(amt)]
            
        table_data.append(row)
        s_no += 1
    
    # Create table
    table = Table(table_data, colWidths=col_widths)
    
    # Table style with clean, minimal borders
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'), # Header alignment
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Data rows alignment
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),    # S.No column
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),      # Particulars column
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),    # HSN column
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),     # All numeric columns from Qty onwards
    ]
    
    # Apply subtle alternating row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9')))
    
    table.setStyle(TableStyle(table_style))
    
    # Calculate table width and center it
    table_width = sum(col_widths)
    table_x = (w - table_width) / 2

    # Draw table with proper positioning
    _w, table_height = table.wrapOn(c, content_width, h)
    table.drawOn(c, table_x, current_y - table_height)

    # ===== TOTALS & FOOTER SECTION =====
    # Position footer elements from the bottom of the page
    footer_y_start = margin + 120

    # --- Totals Table (Right side) ---
    totals_data = []
    if with_gst:
        totals_data.extend([
            ["Subtotal", f"{money(tot_amt - tot_cg - tot_sg)}"],
            ["CGST @ 9%", f"{money(tot_cg)}"],
            ["SGST @ 9%", f"{money(tot_sg)}"],
        ])
    totals_data.append(["Grand Total", f"{money(tot_amt)}"])

    totals_width = 220
    totals_x = w - margin - totals_width
    totals_table = Table(totals_data, colWidths=[120, 100])
    
    totals_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black),
        ('TOPPADDING', (0, -1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
    ])
    totals_table.setStyle(totals_style)

    # Draw totals table and get its actual height
    _w, totals_table_height = totals_table.wrapOn(c, totals_width, h)
    totals_table.drawOn(c, totals_x, footer_y_start)

    # --- Amount in Words (Left side) ---
    # Dynamically position based on the totals table's height to prevent overlap
    amount_in_words_y = footer_y_start + totals_table_height - 15
    amount_in_words_text = num2words(tot_amt, lang='en_IN', to='currency', currency='INR').replace("INR", "Rupees") + " Only"
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(margin, amount_in_words_y, "Amount in Words:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, amount_in_words_y - 15, amount_in_words_text.title())

    # --- Footer Line ---
    footer_line_y = margin + 80
    c.setStrokeColor(primary_color)
    c.setLineWidth(1)
    c.line(margin, footer_line_y, w - margin, footer_line_y)

    # --- Terms & Conditions (Left side) ---
    terms_y = footer_line_y - 15
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, terms_y, "Terms & Conditions:")
    c.setFont("Helvetica", 8)
    c.drawString(margin, terms_y - 12, "1. Goods once sold will not be taken back or exchanged.")
    c.drawString(margin, terms_y - 24, "2. All disputes are subject to Gudivada jurisdiction only.")

    # --- Signature (Right side) ---
    sig_y = footer_line_y - 15
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w - margin, sig_y, f"For {COMPANY['name']}")
    c.setFont("Helvetica", 9)
    c.drawRightString(w - margin, sig_y - 40, "Authorised Signatory")    
    
    # ===== WATERMARK =====
    c.saveState()
    c.setFillColor(colors.Color(0.9, 0.9, 0.9, alpha=0.3))
    c.setFont("Helvetica-Bold", 60)
    c.rotate(45)
    c.drawString(200, -100, "@SSAEW")
    c.restoreState()
    
    c.save()
    buf.seek(0)
    return send_file(buf,
                     download_name=f"invoice_{inv_no}.pdf",
                     mimetype="application/pdf")

# ---------- db setup -----------------------------------------------
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    location = db.Column(db.String(100))
    vehicle_no = db.Column(db.String(20))

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(20), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    cgst = db.Column(db.Numeric(10, 2))
    sgst = db.Column(db.Numeric(10, 2))
    total = db.Column(db.Numeric(10, 2), nullable=False)
    
    customer = db.relationship('Customer', backref=db.backref('invoices', lazy=True))
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    rate = db.Column(db.Numeric(10, 2), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

@APP.cli.command("init-db")
def init_db():
    """Create database tables."""
    with APP.app_context():
        db.create_all()
        print("Initialized the database.")

# ---------- run local ----------------------------------------------
if __name__ == "__main__":
    with APP.app_context():
        db.create_all()  # Create tables if they don't exist
    APP.run(debug=True)