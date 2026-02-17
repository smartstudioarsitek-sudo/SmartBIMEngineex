# modules/utils/pdf_extractor.py
import PyPDF2
import re
import streamlit as st
import json
import google.generativeai as genai

def extract_text_from_pdf(uploaded_file):
    """Mengekstrak teks mentah dari file PDF."""
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error: {e}"

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
    {text_content[:3000]}  # Batasi 3000 karakter agar hemat token
    
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
        st.error(f"Gagal parsing AI: {e}")
        return None
