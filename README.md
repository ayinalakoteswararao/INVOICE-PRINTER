# 📄 Invoice Generator – Python Desktop & Web App

A dual-interface invoice generator that lets you:

1. Create invoices from a clean **Tkinter** desktop GUI (``invoice_generator.py``).
2. Produce the same professional PDF invoices from a **Flask** web app (``invoice-app``).

Both interfaces render the final invoice with **ReportLab**, embed a **QR code** containing GST details, and follow an Indian GST layout.

---

## ✨ Key Features

• Add unlimited line-items with description, HSN, quantity, rate & GST%.  
• Auto-calculates CGST, SGST and grand totals.  
• Produces high-resolution **PDF** invoices on-the-fly.  
• Company branding (logo, address, GSTIN) is fully configurable.  
• Embeds machine-readable **QR code** with invoice meta.  
• Works completely offline; no external services required.

---

## 📂 Project Layout

```
Bill Genration Using Pyhton/
│  README.md               ← you are here
│  invoice_generator.py    ← Stand-alone Tkinter GUI
│
└─ invoice-app/            ← Flask web application
   ├─ app.py               ← Flask routes / PDF generation
   ├─ requirements.txt     ← Python dependencies for the web app
   ├─ templates/           ← Jinja2 HTML templates
   └─ static/              ← logo.png & other assets
```

> Note: The misspelling in the folder name comes from the original upload and is kept to avoid breaking paths.

---

## 🚀 Quick Start

### 1. Clone / Download
```
$ git clone <repo-url>
$ cd "Bill Genration Using Pyhton"
```

### 2. Create a virtualenv (recommended)
```
# Windows
> python -m venv venv
> venv\Scripts\activate

# macOS / Linux
$ python3 -m venv venv
$ source venv/bin/activate
```

### 3. Install dependencies
```
(venv) $ pip install -r invoice-app/requirements.txt
```
This installs **Flask**, **ReportLab**, **qrcode** and **Pillow**.

---

## 🖥️ Running the Desktop GUI

```
(venv) $ python invoice_generator.py
```
A resizable Tkinter window opens where you can enter customer & vehicle details, add items and click **Generate Invoice**.  The PDF is saved in the working directory (e.g. `invoice_0001.pdf`).

---

## 🌐 Running the Web App

### Development server (auto-reload)
```
(venv) $ cd invoice-app
(venv) $ python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

### Production (Gunicorn example)
```
(venv) $ cd invoice-app
(venv) $ gunicorn -w 4 -b 0.0.0.0:8000 app:APP
```

> Change worker count & port as needed.  Deploy behind Nginx or any PaaS that supports WSGI apps.

---

## ⚙️ Configuration

All company-specific values (name, address, GSTIN, logo path, etc.) live in **one place**:

* Desktop GUI → variables inside `InvoiceGenerator.__init__` (``invoice_generator.py``)
* Web app      → the `COMPANY` dict near the top of `invoice-app/app.py`

Replace the default placeholder logo (`static/logo.png`) with your own 300×300 PNG for best results.

---

## 🧪 Tests
No automated tests yet.  Feel free to contribute!

---

## 📜 License
This project is released under the **MIT License** – see `LICENSE` for details.

---

## 🙏 Acknowledgements
• Python core devs 🐍  
• ReportLab for PDF generation  
• Pillow for image processing  
• qrcode library  
• Flask framework  

---

### ✍️ Author
Satya Sai Baba Auto Electrical Works – Gudivada, AP
