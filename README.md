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

# � Invoice Generator Pro

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.0+-black?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-blue?logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

A professional invoice generation system with both **Desktop (Tkinter)** and **Web (Flask)** interfaces, designed specifically for Indian GST compliance with QR code support.

## 🌟 Features

### 📋 Core Features
- 🖥️ **Dual Interface**: Choose between desktop or web interface
- 🧾 **GST Compliant**: Automatically calculates CGST & SGST
- 📄 **PDF Generation**: Professional invoice generation with ReportLab
- 🔍 **QR Code**: Embeds invoice details in QR code
- 💾 **Database**: MySQL integration for data persistence

### �️ Technical Highlights
- 🐍 Built with Python 3.8+
- 🌐 Web interface powered by Flask
- 💽 MySQL database for data storage
- 🎨 Clean, responsive UI
- 🔒 Secure data handling

## � Project Structure

```
Bill-Generation-Using-Python/
│
├── invoice-app/                 # Flask web application
│   ├── app.py                  # Main application file with routes and logic
│   ├── requirements.txt         # Python dependencies
│   ├── config.py               # Configuration settings
│   │
│   ├── static/                 # Static files
│   │   ├── css/               # CSS stylesheets
│   │   ├── js/                # JavaScript files
│   │   └── images/            # Image assets
│   │
│   └── templates/              # HTML templates
│       ├── base.html          # Base template
│       ├── index.html         # Main page
│       └── partials/          # Reusable template components
│
├── invoice_generator.py        # Desktop GUI application
├── requirements.txt            # Main project dependencies
└── README.md                  # Project documentation
```

## �🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- MySQL Server 8.0+
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/invoice-generator.git
   cd invoice-generator
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the database**
   - Create a MySQL database
   - Update the database configuration in `config.py`
   - Initialize the database:
     ```bash
     flask init-db
     ```

5. **Run the application**
   - For web interface:
     ```bash
     cd invoice-app
     flask run
     ```
   - For desktop interface:
     ```bash
     python invoice_generator.py
     ```

## 🖥️ Web Interface

Access the web interface at `http://localhost:5000`

### Features
- 📱 Responsive design
- 🔄 Real-time calculations
- 💾 Auto-save functionality
- 📤 PDF download

## 🖥️ Desktop Interface

Run `invoice_generator.py` to launch the desktop application.

### Features
- 🖱️ Native look and feel
- ⚡ Fast performance
- 💾 Local data storage
- 🖨️ Direct printing support

## 🛠️ Configuration

Edit `config.py` to customize:
- Company details
- GST rates
- Database connection
- Application settings

## 📦 Deployment

### PythonAnywhere
1. Upload your code to PythonAnywhere
2. Set up a new web app
3. Configure the database
4. Set environment variables
5. Install dependencies
6. Initialize the database

## � License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) to get started.

## 📞 Support

For support, email ayinalakoteswararao@gmail.com or open an issue in the GitHub repository.

---

<div align="center">
  Made with ❤️ by Ayinala-KoteswaraRao
</div>
