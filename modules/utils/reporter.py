# modules/utils/reporter.py
import pandas as pd
import io
from fpdf import FPDF

def export_dataframe_to_excel(df):
    """Mengubah DataFrame jadi file Excel bytes."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def export_dataframe_to_csv(df):
    """Mengubah DataFrame jadi CSV bytes."""
    return df.to_csv(index=False).encode('utf-8')

def create_pdf_report(title, content_dict):
    """
    Membuat Laporan PDF Standar.
    content_dict = {"Label": "Value", ...}
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title, 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    for key, value in content_dict.items():
        # Encode latin-1 untuk handle karakter spesial
        clean_key = str(key).encode('latin-1', 'replace').decode('latin-1')
        clean_val = str(value).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, f"{clean_key}: {clean_val}")
        
    return pdf.output(dest='S').encode('latin-1')
