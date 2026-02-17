import streamlit as st
import google.generativeai as genai
import sys
import pandas as pd
import plotly.graph_objects as go
import json
from PIL import Image
import PyPDF2
import re

# --- 1. IMPORT MODULES KITA (MODULAR) ---
# (Pastikan file-file ini sudah dibuat di langkah sebelumnya)
try:
    from core.backend_enginex import EnginexBackend
    from modules.ui.sidebar_manager import render_sidebar
    from modules.utils.reporter import export_dataframe_to_excel, create_pdf_report
    from modules.utils.pdf_extractor import extract_text_from_pdf, ai_parse_structural_data
    
    # Engineering Modules (Import Aman)
    from modules.struktur.validator_sni import cek_dimensi_kolom, cek_rasio_tulangan
    from modules.struktur.peta_gempa_indo import get_data_kota, hitung_respon_spektrum
    try:
        from modules.struktur import libs_fem, libs_beton
    except ImportError: pass

except ImportError as e:
    st.error(f"⚠️ Gagal memuat modul: {e}")
    st.stop()

# --- 2. SETUP APP ---
st.set_page_config(page_title="ENGINEX Ultimate", page_icon="🏗️", layout="wide")

# Init Backend & State
if 'backend' not in st.session_state: st.session_state.backend = EnginexBackend()
db = st.session_state.backend

# State untuk Form Audit (Supaya nilai tidak hilang saat reload)
if 'form_beton' not in st.session_state:
    st.session_state.form_beton = {
        'fc': 25.0, 'fy': 420.0, 'b': 400.0, 'h': 400.0, 
        'd_tul': 16.0, 'n_tul': 8, 'pu': 800.0, 'mu': 150.0
    }

# --- 3. RENDER SIDEBAR (Panggil Modul UI) ---
# Semua setting user disimpan di variabel 'cfg'
cfg = render_sidebar(db)

# Config AI
if cfg.get('api_key'):
    genai.configure(api_key=cfg['api_key'])

# Handle Project Creation (ISO 19650)
if cfg.get('new_project_trigger'):
    # Logika buat folder CDE (simulasi)
    st.toast(f"✅ Proyek {cfg['new_project_trigger']} & CDE Folder dibuat!")

# Handle Reset Chat
if cfg.get('reset_trigger'):
    db.clear_chat(cfg['active_project'], cfg.get('persona', 'User'))
    st.rerun()


# ==========================================
# 4. ROUTING MENU UTAMA
# ==========================================

# --- A. MENU AI ASSISTANT ---
if cfg['menu'] == "🤖 AI Assistant":
    st.header(f"🤖 AI Assistant ({cfg.get('model_type', 'Default')})")
    
    # Tampilkan Chat History
    active_persona = cfg.get('persona', "General")
    history = db.get_chat_history(cfg['active_project'], active_persona)
    
    for msg in history:
        with st.chat_message(msg['role']): st.markdown(msg['content'])
        
    # Input User
    prompt = st.chat_input("Perintah Anda...")
    if prompt:
        with st.chat_message("user"): st.markdown(prompt)
        db.simpan_chat(cfg['active_project'], active_persona, "user", prompt)
        
        # Siapkan Konteks File (Jika ada)
        full_prompt = [prompt]
        if cfg.get('files'):
            for f in cfg['files']:
                if f.type == "application/pdf":
                    # Panggil Utils PDF
                    txt = extract_text_from_pdf(f)
                    full_prompt.append(f"Isi PDF {f.name}:\n{txt}")
                elif f.type.startswith("image"):
                    full_prompt.append(Image.open(f))
        
        # Panggil Gemini
        with st.chat_message("assistant"):
            with st.spinner("Berpikir..."):
                try:
                    model = genai.GenerativeModel(cfg['model_type']) # Pake pilihan user
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    db.simpan_chat(cfg['active_project'], active_persona, "assistant", response.text)
                except Exception as e:
                    st.error(f"Error AI: {e}")


# --- B. MENU FEM (GEMPA) ---
elif cfg['menu'] == "🌪️ Analisis Gempa (FEM)":
    st.header("🌪️ Analisis Gempa Dinamis")
    
    # 1. Peta Gempa (Panggil Modul Peta)
    with st.expander("🌍 Data Gempa (SNI 1726)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            db_kota = get_data_kota()
            kota = st.selectbox("Lokasi", list(db_kota.keys()), index=8)
            data_g = db_kota[kota]
            ss = st.number_input("Ss", value=data_g['Ss'], disabled=(kota!="Pilih Manual"))
            s1 = st.number_input("S1", value=data_g['S1'], disabled=(kota!="Pilih Manual"))
        with c2:
            situs = st.selectbox("Tanah", ["SA (Keras)", "SD (Sedang)", "SE (Lunak)"])
            # Hitung Respon Spektrum
            res_gempa = hitung_respon_spektrum(ss, s1, situs.split()[0])
            st.info(f"SDS: {res_gempa['SDS']:.3f} | SD1: {res_gempa['SD1']:.3f}")

    # 2. Input & Run
    if st.button("🚀 Run Analysis"):
        if 'libs_fem' in sys.modules:
            engine = libs_fem.OpenSeesEngine()
            # (Logic build model disederhanakan untuk contoh konektor)
            df_res = engine.run_modal_analysis() 
            st.dataframe(df_res)
            
            # 3. Export (Panggil Modul Reporter)
            xls = export_dataframe_to_excel(df_res)
            st.download_button("📥 Download Excel", xls, "Analisis_Gempa.xlsx")
        else:
            st.warning("Engine FEM belum siap.")


# --- C. MENU AUDIT STRUKTUR ---
elif cfg['menu'] == "🏗️ Audit Struktur":
    st.header("🏗️ Audit Forensik Struktur")
    
    # 1. PDF Auto-Fill (Panggil Utils PDF)
    with st.expander("📂 Import dari Laporan (PDF)"):
        f_pdf = st.file_uploader("Upload DED/Laporan", type="pdf")
        if f_pdf and st.button("Ekstrak Data"):
            txt = extract_text_from_pdf(f_pdf)
            data = ai_parse_structural_data(txt, cfg['api_key'])
            if data:
                # Update Session State
                st.session_state.form_beton.update(data)
                st.success("Formulir terisi otomatis!")
                st.rerun()

    # 2. Form Input (Terhubung ke Session State)
    col1, col2 = st.columns(2)
    b = col1.number_input("Lebar (b)", value=st.session_state.form_beton.get('b', 400.0))
    h = col2.number_input("Tinggi (h)", value=st.session_state.form_beton.get('h', 400.0))
    # ... (Input lain bisa ditambahkan sesuai kebutuhan) ...

    # 3. Validasi & Hitung
    if st.button("🚀 Cek & Hitung"):
        # Panggil Validator SNI
        errs = cek_dimensi_kolom(b, h, 5)
        if errs:
            for e in errs: st.error(e)
        else:
            st.success("✅ Geometri OK")
            # Panggil Libs Beton (Contoh dummy call)
            # res = libs_beton.analyze(...) 
            # st.write(res)
            
            # Export Laporan (Panggil Modul Reporter)
            pdf_bytes = create_pdf_report("Laporan Audit", {"Dimensi": f"{b}x{h}", "Status": "Aman"})
            st.download_button("📄 Download PDF Laporan", pdf_bytes, "Laporan_Audit.pdf")
