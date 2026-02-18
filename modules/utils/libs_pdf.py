from fpdf import FPDF
import re
from datetime import datetime

def clean_text_for_report(text):
    # Bersihkan markdown code block
    clean = re.sub(r"```python.*?```", "[CODE REMOVED FOR PDF]", text, flags=re.DOTALL)
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    # Bersihkan bold marker markdown (**) karena fpdf tidak baca markdown
    clean = clean.replace("**", "").replace("##", "").replace("#", "")
    return clean.strip()

class ProfessionalPDF(FPDF):
    def __init__(self, title, project_code="STR-2026"):
        super().__init__()
        self.doc_title = title
        self.project_code = project_code
        
    def header(self):
        # --- 1. LOGO & KOP SURAT (Standar PBG) ---
        # Ganti 'logo.png' dengan path logo perusahaan Anda jika ada
        # try:
        #     self.image('assets/logo_perusahaan.png', 10, 8, 33)
        # except:
        #     pass 
            
        # Font untuk Kop Surat
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'KONSULTAN PERENCANA STRUKTUR & SIPIL', 0, 1, 'R')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'SmartBIM Enginex System | ISO 19650 Compliant Environment', 0, 1, 'R')
        self.cell(0, 5, 'Dokumen Teknis Persetujuan Bangunan Gedung (PBG)', 0, 1, 'R')
        
        # Garis Pembatas Kop
        self.set_line_width(0.5)
        self.line(10, 25, 200, 25)
        self.ln(20) # Spasi setelah kop

        # Judul Halaman
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, self.doc_title, 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # --- 2. DOCUMENT CONTROL (Standar ISO 19650) ---
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128) # Abu-abu
        
        # Kiri: Tanggal Cetak
        date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        self.cell(0, 10, f'Dicetak: {date_str} | Status: DRAFT REVIEW', 0, 0, 'L')
        
        # Kanan: Halaman X dari Y
        self.cell(0, 10, f'Halaman {self.page_no()} dari {{nb}}', 0, 0, 'R')

def create_pdf(text_content, title="LAPORAN PERHITUNGAN STRUKTUR"):
    # Inisialisasi Class PDF Custom
    pdf = ProfessionalPDF(title=title)
    pdf.alias_nb_pages() # Untuk hitung total halaman
    pdf.add_page()
    pdf.set_font("Times", size=11) # Times New Roman standar laporan teknik
    
    # 3. HANDLING TEXT & PARAGRAPH
    clean_content = clean_text_for_report(text_content)
    
    # Encode latin-1 (Wajib untuk FPDF standar)
    try:
        clean_content = clean_content.encode('latin-1', 'replace').decode('latin-1')
    except:
        pass

    # Trik sederhana agar baris tidak terlalu rapat
    pdf.multi_cell(0, 6, clean_content)
    
    # 4. SIGNATURE BLOCK (Kolom Tanda Tangan) - Standar Laporan
    pdf.add_page() # Halaman baru untuk tanda tangan
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "LEMBAR PENGESAHAN (APPROVAL SHEET)", 0, 1, 'C')
    pdf.ln(20)
    
    col_width = 60
    # Header Tabel Tanda Tangan
    pdf.cell(col_width, 10, "Dibuat Oleh (Drafter)", 1, 0, 'C')
    pdf.cell(col_width, 10, "Diperiksa (Engineer)", 1, 0, 'C')
    pdf.cell(col_width, 10, "Disetujui (Principal)", 1, 1, 'C')
    
    # Kotak Kosong Tanda Tangan
    pdf.cell(col_width, 30, "", 1, 0, 'C')
    pdf.cell(col_width, 30, "", 1, 0, 'C')
    pdf.cell(col_width, 30, "", 1, 1, 'C')
    
    # Nama (Placeholder)
    pdf.cell(col_width, 10, "( AI Assistant )", 1, 0, 'C')
    pdf.cell(col_width, 10, "( Senior Engineer )", 1, 0, 'C')
    pdf.cell(col_width, 10, "( The Grandmaster )", 1, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')
