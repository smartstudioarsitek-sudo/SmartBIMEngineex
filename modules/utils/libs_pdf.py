# modules/utils/libs_pdf.py
from fpdf import FPDF
import re
from datetime import datetime

def clean_text_for_report(text):
    # 1. Bersihkan Code Block Python
    clean = re.sub(r"```python.*?```", "[KODE DIHAPUS UNTUK PDF]", text, flags=re.DOTALL)
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    
    # 2. PEMBERSIHAN LATEX MATEMATIKA (Agar tidak jadi bahasa alien)
    clean = clean.replace("$", "") # Hapus semua simbol dollar
    clean = clean.replace(r"\times", " x ").replace(r"\geq", " >= ").replace(r"\leq", " <= ")
    clean = clean.replace(r"\Delta", "Delta ").replace(r"\Sigma", "Sigma ")
    clean = clean.replace(r"\epsilon", "Regangan ").replace(r"\gamma", "Gamma ")
    clean = clean.replace(r"\_", "_").replace(r"\^", "^")
    clean = clean.replace(r"\left", "").replace(r"\right", "")
    # Konversi \sqrt{x} jadi akar(x) dan \frac{x}{y} jadi (x)/(y)
    clean = re.sub(r"\\sqrt\{(.*?)\}", r"akar(\1)", clean)
    clean = re.sub(r"\\frac\{(.*?)\}\{(.*?)\}", r"(\1) / (\2)", clean)
    clean = clean.replace("\\", "") # Hapus sisa backslash
    
    # 3. PEMBERSIHAN TABEL MARKDOWN (Ubah ke format teks lurus ber spasi)
    clean = re.sub(r"\|-.*?-+\|", "", clean) # Hapus baris pemisah tabel |--|--|
    clean = clean.replace(" | ", "  -  ").replace("|", "")
    
    # 4. Bersihkan Markdown Bold/Italic/Heading
    clean = clean.replace("**", "").replace("*", "").replace("##", "").replace("#", "")
    
    # 5. Normalisasi Baris Kosong agar tidak terlalu renggang
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    
    return clean.strip()

class ProfessionalPDF(FPDF):
    def __init__(self, title, project_code="STR-2026"):
        super().__init__()
        self.doc_title = title
        self.project_code = project_code
        
    def header(self):
        # Font untuk Kop Surat
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'KONSULTAN PERENCANA STRUKTUR & SIPIL', 0, 1, 'R')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'SmartBIM Enginex System | ISO 19650 Compliant', 0, 1, 'R')
        self.cell(0, 5, 'Dokumen Teknis Persetujuan Bangunan Gedung (PBG)', 0, 1, 'R')
        
        # Garis Pembatas
        self.set_line_width(0.5)
        self.line(10, 25, 200, 25)
        self.ln(15) 

        # Judul Laporan
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, self.doc_title.upper(), 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
        self.cell(0, 10, f'Dicetak otomatis oleh AI: {date_str}', 0, 0, 'L')
        self.cell(0, 10, f'Halaman {self.page_no()} dari {{nb}}', 0, 0, 'R')

def create_pdf(text_content, title="LAPORAN PERHITUNGAN STRUKTUR"):
    pdf = ProfessionalPDF(title=title)
    pdf.alias_nb_pages() 
    pdf.add_page()
    
    # Gunakan Arial biasa ukuran 11 (Aman untuk ASCII/Latin-1)
    pdf.set_font("Arial", size=11) 
    
    clean_content = clean_text_for_report(text_content)
    
    try:
        clean_content = clean_content.encode('latin-1', 'replace').decode('latin-1')
    except:
        pass

    pdf.multi_cell(0, 6, clean_content)
    
    # Blok Tanda Tangan
    pdf.add_page()
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "LEMBAR PENGESAHAN", 0, 1, 'C')
    pdf.ln(15)
    
    col_w = 60
    pdf.cell(col_w, 10, "Dibuat Oleh (Drafter AI)", 0, 0, 'C')
    pdf.cell(col_w, 10, "Diperiksa (Engineer)", 0, 0, 'C')
    pdf.cell(col_w, 10, "Disetujui (Principal)", 0, 1, 'C')
    
    pdf.cell(col_w, 25, "", 0, 0, 'C')
    pdf.cell(col_w, 25, "", 0, 0, 'C')
    pdf.cell(col_w, 25, "", 0, 1, 'C')
    
    pdf.cell(col_w, 5, "( SmartBIM Engineex )", 0, 0, 'C')
    pdf.cell(col_w, 5, "( .............................. )", 0, 0, 'C')
    pdf.cell(col_w, 5, "( .............................. )", 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')
