# invoice_generator.py
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader

try:
    from PIL import Image, ImageTk                 # GUI logo
except ImportError:
    Image = ImageTk = None

import qrcode                                       # QR code


def money(val: Decimal) -> str:
    """Format Decimal to 2-dp string."""
    return f"{val.quantize(Decimal('0.01'), ROUND_HALF_UP)}"


class InvoiceGenerator:
    """GUI app that produces a tax-invoice PDF."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Invoice Generator")
        self.root.geometry("950x680")

        # ─── runtime data ─────────────────────────────────────────────
        self.items: list[dict] = []
        self.invoice_number: int = 1

        # ─── constants you may edit ──────────────────────────────────
        self.logo_path = "Bosch Logo.png"
        self.company_name = "SATYA SAI BABA AUTO ELECTRICAL WORKS"
        self.company_tag = "Authorised MICO BOSCH Service"
        self.company_addr_1 = (
            "Venkateswara Theatre Road, Near I M A Hall, Ganga Enclave"
        )
        self.company_addr_2 = "Satyanarayana Puram, GUDIVADA – 521 301"
        self.company_state = "Andhra Pradesh  ·  State Code : 37"
        self.company_phone = "Cell : 9958592564   8074546541"
        self.gstin = "GSTIN : 37CYCP5977H1ZM"

        # GST defaults
        self.default_gst = Decimal("18.0")  # %
        self.cgst_rate = self.default_gst / 2
        self.sgst_rate = self.default_gst / 2

        # ─── styles ──────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Arial", 12))
        style.configure("TEntry", font=("Arial", 12))
        style.configure("TButton", font=("Arial", 12), padding=4)
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # ── header (logo + company) ──────────────────────────────────
        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew")
        if ImageTk and os.path.isfile(self.logo_path):
            img = Image.open(self.logo_path).resize((70, 70))
            self.tk_logo = ImageTk.PhotoImage(img)
            tk.Label(header, image=self.tk_logo).pack(side=tk.LEFT, padx=5)
        tk.Label(
            header, text=self.company_name, font=("Arial", 20, "bold"), fg="#0A4D91"
        ).pack(side=tk.LEFT, padx=10)

        # ── customer / meta info ─────────────────────────────────────
        cust = ttk.LabelFrame(main, text="Customer & Job Information", padding=10)
        cust.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        labels = [
            ("Customer Name", 0, 0),
            ("Customer Address", 1, 0),
            ("Vehicle No.", 0, 2),
            ("Job-Card No.", 1, 2),
            ("PO No.", 0, 4),
        ]
        for text, r, c in labels:
            ttk.Label(cust, text=text + ":").grid(row=r, column=c, sticky="w", padx=4)
        self.customer_name = ttk.Entry(cust, width=28)
        self.customer_addr = ttk.Entry(cust, width=28)
        self.vehicle_no = ttk.Entry(cust, width=18)
        self.job_card = ttk.Entry(cust, width=18)
        self.po_no = ttk.Entry(cust, width=18)
        self.customer_name.grid(row=0, column=1, padx=4)
        self.customer_addr.grid(row=1, column=1, padx=4)
        self.vehicle_no.grid(row=0, column=3, padx=4)
        self.job_card.grid(row=1, column=3, padx=4)
        self.po_no.grid(row=0, column=5, padx=4)

        # ── item entry ───────────────────────────────────────────────
        add = ttk.LabelFrame(main, text="Add Item", padding=10)
        add.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        for i, (txt, w) in enumerate(
            [
                ("Description", 28),
                ("HSN", 10),
                ("Qty", 6),
                ("Rate", 10),
                ("%GST", 6),
            ]
        ):
            ttk.Label(add, text=txt + ":").grid(row=i, column=0, sticky="w")
        self.desc_e = ttk.Entry(add, width=28)
        self.hsn_e = ttk.Entry(add, width=10)
        self.qty_e = ttk.Entry(add, width=6)
        self.rate_e = ttk.Entry(add, width=10)
        self.gst_e = ttk.Entry(add, width=6)
        self.desc_e.grid(row=0, column=1, padx=4, pady=2, sticky="w")
        self.hsn_e.grid(row=1, column=1, padx=4, pady=2, sticky="w")
        self.qty_e.grid(row=2, column=1, padx=4, pady=2, sticky="w")
        self.rate_e.grid(row=3, column=1, padx=4, pady=2, sticky="w")
        self.gst_e.grid(row=4, column=1, padx=4, pady=2, sticky="w")
        self.gst_e.insert(0, str(self.default_gst))

        ttk.Button(add, text="Add Item", command=self.add_item).grid(
            row=4, column=2, padx=10
        )

        # ── items table ──────────────────────────────────────────────
        items_f = ttk.LabelFrame(main, text="Invoice Items", padding=10)
        items_f.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        cols = (
            "sl",
            "desc",
            "hsn",
            "qty",
            "rate",
            "taxable",
            "cgst",
            "sgst",
            "net",
        )
        self.tree = ttk.Treeview(items_f, columns=cols, show="headings", height=10)
        headings = [
            ("sl", "Sl.", 40),
            ("desc", "Description", 200),
            ("hsn", "HSN", 70),
            ("qty", "Qty", 50),
            ("rate", "Rate", 80),
            ("taxable", "Taxable", 90),
            ("cgst", f"CGST {self.cgst_rate}% ", 100),
            ("sgst", f"SGST {self.sgst_rate}% ", 100),
            ("net", "Amount", 100),
        ]
        for col, txt, w in headings:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # ── totals row ───────────────────────────────────────────────
        total_f = ttk.Frame(main)
        total_f.grid(row=4, column=0, sticky="e", padx=10)
        ttk.Label(total_f, text="Taxable Value:").grid(row=0, column=0, sticky="e")
        ttk.Label(total_f, text="CGST:").grid(row=1, column=0, sticky="e")
        ttk.Label(total_f, text="SGST:").grid(row=2, column=0, sticky="e")
        ttk.Label(total_f, text="Grand Total:").grid(row=3, column=0, sticky="e")
        self.taxable_l = ttk.Label(total_f, text="0.00", width=12)
        self.cgst_l = ttk.Label(total_f, text="0.00", width=12)
        self.sgst_l = ttk.Label(total_f, text="0.00", width=12)
        self.net_l = ttk.Label(total_f, text="0.00", width=12, font=("Arial", 12, "bold"))
        for i, lab in enumerate(
            (self.taxable_l, self.cgst_l, self.sgst_l, self.net_l)
        ):
            lab.grid(row=i, column=1, sticky="e")

        # ── action buttons ───────────────────────────────────────────
        act = ttk.Frame(main, padding=10)
        act.grid(row=5, column=0, sticky="e")
        ttk.Button(act, text="Generate Invoice", command=self.generate_pdf).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(act, text="Clear All", command=self.clear_all).pack(
            side=tk.LEFT, padx=5
        )

        # resize rules
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

    # ─────────────────── internal helpers ────────────────────────────
    def _calc_totals(self):
        taxable = sum(item["taxable"] for item in self.items)
        cgst = sum(item["cgst"] for item in self.items)
        sgst = sum(item["sgst"] for item in self.items)
        net = taxable + cgst + sgst
        return taxable, cgst, sgst, net

    def _refresh_totals_display(self):
        taxable, cgst, sgst, net = self._calc_totals()
        self.taxable_l.config(text=money(taxable))
        self.cgst_l.config(text=money(cgst))
        self.sgst_l.config(text=money(sgst))
        self.net_l.config(text=money(net))

    # ─────────────────── GUI callbacks ───────────────────────────────
    def add_item(self):
        try:
            desc = self.desc_e.get().strip()
            hsn = self.hsn_e.get().strip()
            qty = Decimal(self.qty_e.get())
            rate = Decimal(self.rate_e.get())
            gst_rate = Decimal(self.gst_e.get())
        except Exception:
            messagebox.showerror("Input Error", "Please enter valid numbers.")
            return
        if not desc or qty <= 0 or rate <= 0 or gst_rate < 0:
            messagebox.showerror("Input Error", "Invalid item details.")
            return

        taxable = qty * rate
        cgst = taxable * gst_rate / 200  # half of GST
        sgst = taxable * gst_rate / 200
        net = taxable + cgst + sgst

        self.items.append(
            dict(
                desc=desc,
                hsn=hsn,
                qty=qty,
                rate=rate,
                taxable=taxable,
                cgst=cgst,
                sgst=sgst,
                net=net,
            )
        )
        self.tree.insert(
            "",
            "end",
            values=(
                len(self.items),
                desc,
                hsn,
                qty,
                money(rate),
                money(taxable),
                money(cgst),
                money(sgst),
                money(net),
            ),
        )
        self._refresh_totals_display()

        # clear entry widgets
        for e in (self.desc_e, self.hsn_e, self.qty_e, self.rate_e):
            e.delete(0, tk.END)
        self.gst_e.delete(0, tk.END)
        self.gst_e.insert(0, str(self.default_gst))

    def generate_pdf(self):
        if not self.items:
            messagebox.showerror("No Items", "Add at least one item.")
            return
        if not self.customer_name.get().strip():
            messagebox.showerror("Missing", "Enter customer name.")
            return

        pdf_name = f"invoice_{self.invoice_number:04}.pdf"
        c = canvas.Canvas(pdf_name, pagesize=letter)
        width, height = letter

        # header logo + company
        if os.path.isfile(self.logo_path):
            c.drawImage(
                ImageReader(self.logo_path),
                40,
                height - 100,
                width=60,
                preserveAspectRatio=True,
                mask="auto",
            )
        tx = 110 if os.path.isfile(self.logo_path) else 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(tx, height - 40, self.company_name)
        c.setFont("Helvetica", 11)
        for i, line in enumerate(
            [
                self.company_tag,
                self.company_addr_1,
                self.company_addr_2,
                self.company_state,
                self.company_phone,
                self.gstin,
            ],
            start=1,
        ):
            c.drawString(tx, height - 40 - 15 * i, line)

        # invoice meta
        c.setFont("Helvetica-Bold", 18)
        c.drawString(40, height - 160, "TAX INVOICE")
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 40, height - 160, f"Invoice #: {self.invoice_number:04}")
        c.drawRightString(
            width - 40, height - 175, f"Date : {datetime.now():%d-%m-%Y}"
        )

        # customer block
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, height - 200, "Bill To :")
        c.setFont("Helvetica", 11)
        c.drawString(100, height - 200, self.customer_name.get().strip())
        c.drawString(100, height - 215, self.customer_addr.get().strip())
        meta_y = height - 200
        c.drawString(width - 300, meta_y, f"Vehicle No.: {self.vehicle_no.get().strip()}")
        c.drawString(width - 300, meta_y - 15, f"Job-Card No.: {self.job_card.get().strip()}")
        c.drawString(width - 300, meta_y - 30, f"PO No.: {self.po_no.get().strip()}")

        # table header
        y = height - 245
        c.setFont("Helvetica-Bold", 11)
        headers = [
            ("Sl.", 45),
            ("Description", 75),
            ("HSN", 250),
            ("Qty", 300),
            ("Rate", 340),
            ("Taxable", 400),
            ("CGST", 465),
            ("SGST", 520),
            ("Amount", 575),
        ]
        for text, x in headers:
            c.drawString(x, y, text)
        c.line(40, y - 3, width - 40, y - 3)

        # rows
        y -= 18
        c.setFont("Helvetica", 10)
        for idx, it in enumerate(self.items, 1):
            c.drawString(45, y, str(idx))
            c.drawString(75, y, it["desc"])
            c.drawString(250, y, it["hsn"])
            c.drawRightString(330, y, str(it["qty"]))
            c.drawRightString(390, y, money(it["rate"]))
            c.drawRightString(455, y, money(it["taxable"]))
            c.drawRightString(510, y, money(it["cgst"]))
            c.drawRightString(565, y, money(it["sgst"]))
            c.drawRightString(width - 45, y, money(it["net"]))
            y -= 16

        # totals
        taxable, cgst, sgst, net = self._calc_totals()
        c.line(390, y + 5, width - 40, y + 5)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(420, y - 10, "Totals :")
        c.drawRightString(455, y - 10, money(taxable))
        c.drawRightString(510, y - 10, money(cgst))  
        c.drawRightString(565, y - 10, money(sgst))
        c.drawRightString(width - 45, y - 10, money(net))

        # footer text
        c.setFont("Helvetica", 10)
        c.drawString(
            40,
            70,
            "Goods once sold cannot be taken back. Disputes are subject to Gudivada jurisdiction only.",
        )
        c.drawRightString(width - 40, 70, f"For {self.company_name}")
        c.drawRightString(width - 40, 55, "Proprietor")

        # QR code
        qr_data = f"{self.gstin}|{self.invoice_number:04}|{datetime.now():%d%m%Y}|{money(net)}"
        qr_img = qrcode.make(qr_data)
        buf = BytesIO()
        qr_img.save(buf)
        buf.seek(0)
        c.drawImage(ImageReader(buf), width - 120, 80, 70, 70)

        c.save()
        messagebox.showinfo("Done", f"Created {pdf_name}")
        self.invoice_number += 1
        self.clear_all()

    def clear_all(self):
        # clear all entries and table
        for widget in (
            self.customer_name,
            self.customer_addr,
            self.vehicle_no,
            self.job_card,
            self.po_no,
            self.desc_e,
            self.hsn_e,
            self.qty_e,
            self.rate_e,
            self.gst_e,
        ):
            widget.delete(0, tk.END)
        self.gst_e.insert(0, str(self.default_gst))
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.items.clear()
        self._refresh_totals_display()


if __name__ == "__main__":
    root = tk.Tk()
    app = InvoiceGenerator(root)
    root.mainloop()