from io import BytesIO
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import os, json

from flask import Flask, render_template, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image

# ---------- config  -------------------------------------------------
APP = Flask(__name__)

COMPANY = {
    "name":  "SATYA SAI BABA AUTO ELECTRICAL WORKS",
    "tag":   "Authorised MICO BOSCH Service",
    "addr1": "Venkateswara Theatre Rd, Near IMA Hall, Ganga Enclave",
    "addr2": "Satyanarayana Puram, GUDIVADA – 521 301",
    "state": "Andhra Pradesh · State Code : 37",
    "phone": "Cell : 9958592564   8074546541",
    "gstin": "GSTIN : 37CYCP5977H1ZM",
    "logo":  os.path.join("static", "logo.png"),
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

    # ----- build PDF in memory -------------------------------------
    buf = BytesIO()
    c   = canvas.Canvas(buf, pagesize=letter)
    w,h = letter

    # logo / header
    if os.path.exists(COMPANY["logo"]):
        c.drawImage(ImageReader(COMPANY["logo"]), 45, h-100, width=60, mask="auto")
    tx = 115 if os.path.exists(COMPANY["logo"]) else 45
    c.setFont("Helvetica-Bold",14); c.drawString(tx,h-40,COMPANY["name"])
    c.setFont("Helvetica",11)
    for i,line in enumerate([COMPANY["tag"],COMPANY["addr1"],COMPANY["addr2"],
                             COMPANY["state"],COMPANY["phone"],COMPANY["gstin"]],1):
        c.drawString(tx,h-40-15*i,line)

    # title/meta
    c.setFont("Helvetica-Bold",18); c.drawString(45,h-160,"TAX INVOICE")
    c.setFont("Helvetica-Bold",12)
    c.drawRightString(w-45,h-160,f"Invoice #: {inv_no}")
    c.drawRightString(w-45,h-175,f"Date : {datetime.now():%d-%m-%Y}")

    # customer / vehicle block -------------------------------------------------
    c.setFont("Helvetica-Bold",12)
    c.drawString(45, h-185, "Bill To :")
    c.setFont("Helvetica", 11)
    left_start = 120  # consistent indent for all customer lines
    c.drawString(left_start, h-185, cust["name"])
    c.drawString(left_start, h-200, cust["address"])

    # right-hand meta block (shift slightly left for long values)
    right_start = w - 270
    c.drawString(right_start, h-185, f"Vehicle No.: {cust['vehicle']}")
    c.drawString(right_start, h-200, f"Job-Card No.: {cust['jobcard']}")
    c.drawString(right_start, h-215, f"PO No.: {cust['po']}")

    # column positions (fit within page width 612pt)
    if with_gst:
        COL = dict(sl=50, desc=80, hsn=245, qty=305, rate=365,
                   tax=425, cgst=485, sgst=545, amt=590, right=590)
        heads = [
            ("Sl.", "sl"),
            ("Description", "desc"),
            ("HSN", "hsn"),
            ("Qty", "qty"),
            ("Rate", "rate"),
            ("Taxable", "tax"),
            (f"CGST {cgst_rate}%", "cgst"),
            (f"SGST {sgst_rate}%", "sgst"),
            ("Amount", "amt"),
        ]
    else:
        COL = dict(sl=50, desc=80, hsn=245, qty=305, rate=365,
                   amt=590, right=590)
        heads = [
            ("Sl.", "sl"),
            ("Description", "desc"),
            ("HSN", "hsn"),
            ("Qty", "qty"),
            ("Rate", "rate"),
            ("Amount", "amt"),
        ]

    # table header
    y=h-240; c.setFont("Helvetica-Bold",10)
    for t,k in heads: c.drawString(COL[k],y,t)
    c.line(COL["sl"],y-3,COL["right"],y-3)

    # rows
    y-=18; c.setFont("Helvetica",10)
    D  = Decimal
    tot_tax = tot_cg = tot_sg = tot_amt = D("0")
    for i,it in enumerate(items,1):
        qty,rate = D(it["qty"]), D(it["rate"])
        tax=qty*rate; cg=tax*cgst_rate/100; sg=tax*sgst_rate/100; amt=tax+cg+sg
        tot_tax+=tax; tot_cg+=cg; tot_sg+=sg; tot_amt+=amt
        row=[(i,"sl"),(it["desc"],"desc"),(it["hsn"],"hsn"),
             (qty,"qty"),(money(rate),"rate")] 
        if with_gst:
            row += [(money(tax),"tax"),(money(cg),"cgst"),(money(sg),"sgst"),(money(amt),"amt")]
        else:
            row += [(money(amt),"amt")]
        for txt,k in row:
            if k in ("rate","tax","cgst","sgst","amt"):
                c.drawRightString(COL[k],y,str(txt))
            else: c.drawString(COL[k],y,str(txt))
        y-=14

    # totals
    c.line(COL["rate"],y+5,COL["right"],y+5)
    c.setFont("Helvetica-Bold",10)
    totals=[("Taxable", tot_tax)]
    if with_gst:
        totals += [("CGST", tot_cg), ("SGST", tot_sg)]
    totals += [("Grand Total", tot_amt)]
    for lab,val in totals:
        y -= 12
        # choose column for label (use tax column if present else rate)
        label_x = COL["tax"] if "tax" in COL else COL["rate"]
        c.drawString(label_x, y, f"{lab} :")  # left-align label
        c.drawRightString(COL["right"], y, money(val))

    # footer (disclaimer left, signature right)
    c.setFont("Helvetica",9)
    c.drawString(45,90,"Goods once sold cannot be taken back.")
    c.drawString(45,75,"Disputes are subject to Gudivada jurisdiction only.")

    # signature block on right, slightly lower to avoid overlap
    c.setFont("Helvetica",9)
    c.drawRightString(w-45,50,"For "+COMPANY["name"])
    c.drawRightString(w-45,35,"Proprietor")

    # place QR at top-right near header instead of footer
    qr = qrcode.make(f"{COMPANY['gstin']}|{inv_no}|{datetime.now():%d%m%Y}|{money(tot_amt)}")
    qbuf = BytesIO(); qr.save(qbuf); qbuf.seek(0)
    c.drawImage(ImageReader(qbuf), COL["right"]-70, h-140, 70, 70)

    c.save()

    buf.seek(0)
    return send_file(buf,
                     download_name=f"invoice_{inv_no}.pdf",
                     mimetype="application/pdf")

# ---------- run local ----------------------------------------------
if __name__ == "__main__":
    APP.run(debug=True) 