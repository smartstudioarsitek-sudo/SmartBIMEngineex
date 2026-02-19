# modules/utils/pdf_extractor.py
import pdfplumber
import re
import streamlit as st
import json
import google.generativeai as genai

def extract_text_from_pdf(uploaded_file):
    """
    Lebih cerdas mengekstrak tabel dan layout menggunakan pdfplumber.
    Cocok untuk laporan teknik yang banyak mengandung tabel.
    """
    text = ""
    try:
        # pdfplumber butuh file path atau file-like object
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # 1. STRATEGI TABEL: Ambil data tabel terlebih dahulu
                # Laporan struktur 80% datanya ada di tabel
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Bersihkan None values dan gabung dengan delimiter pipa |
                        # Ini membantu AI membedakan kolom
                        clean_row = [str(cell) if cell is not None else "" for cell in row]
                        text += " | ".join(clean_row) + "\n"
                
                text += "\n--- TEKS HALAMAN ---\n"
                
                # 2. STRATEGI TEKS: Ambil sisa teks biasa
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        return text
    except Exception as e:
        return f"Error membaca PDF: {e}"

def ai_parse_structural_data(text_content, api_key):
    """
    Menggunakan Gemini untuk mencari parameter struktur (fc, fy, dimensi) 
    dari teks laporan yang berantakan.
    """
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Bertindaklah sebagai Data Entry Engineer.
    Tugas: Ekstrak parameter struktur beton dari teks laporan berikut menjadi format JSON.
    
    Cari nilai-nilai ini (jika tidak ada, isi null):
    - fc (Mutu Beton dalam MPa. Jika K-xxx, konversi ke MPa: K/10 * 0.83)
    - fy (Mutu Baja Tulangan dalam MPa)
    - b_kolom (Lebar kolom dalam mm)
    - h_kolom (Tinggi kolom dalam mm)
    - diameter_tulangan (Diameter besi utama dalam mm)
    - jumlah_tulangan (Jumlah batang besi)
    - pu (Beban Aksial dalam kN)
    - mu (Momen dalam kNm)

    Teks Laporan:
    {text_content[:4000]}  # Batasi karakter agar hemat token
    
    Output WAJIB JSON murni tanpa markdown:
    {{
        "fc": 25.0,
        "fy": 400.0,
        ...
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        # st.error(f"Gagal parsing AI: {e}") # Silent error agar UI tidak berantakan
        return None
