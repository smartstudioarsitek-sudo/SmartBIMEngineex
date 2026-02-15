import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from PIL import Image
import PyPDF2
import io
import docx
import zipfile
from pptx import Presentation
import re
import os
from fpdf import FPDF 

# ==========================================
# 1. IMPORT LIBRARY ENGINEERING (MODULAR)
# ==========================================
try:
    # Core
    from core.backend_enginex import EnginexBackend
    from core.persona import gems_persona, get_persona_list

    # Modules
    from modules.struktur import libs_sni, libs_baja, libs_bridge, libs_gempa
    from modules.water import libs_hidrologi, libs_irigasi, libs_jiat, libs_bendung
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research
    from modules.arch import libs_arch, libs_zoning, libs_green
    from modules.utils import libs_pdf, libs_export, libs_bim_importer
    
    # Optional Geotek (jika file ada)
    try: from modules.geotek import libs_geoteknik, libs_pondasi
    except: pass

except ImportError as e:
    st.error(f"⚠️ **SISTEM ERROR: Gagal Import Modul**")
    st.code(str(e))
    st.stop()

# ==========================================
# 2. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="ENGINEX Ultimate", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 5px;}
    .sub-header {font-size: 14px; color: #64748B; margin-bottom: 20px;}
    [data-testid="stSidebar"] {background-color: #F8FAFC; border-right: 1px solid #E2E8F0;}
    .stChatInput textarea {font-size: 16px !important;}
    .stDownloadButton button {width: 100%; border-radius: 6px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. ENGINE EKSEKUSI (LOGIC INJECTION)
# ==========================================
def execute_generated_code(code_str, file_ifc_path=None):
    """Menjalankan kode Python AI dengan akses ke Library Engineering"""
    try:
        local_vars = {
            "pd": pd, "np": np, "plt": plt, "st": st,
            
            # Daftarkan semua library di sini agar AI kenal
            "libs_sni": libs_sni, "libs_baja": libs_baja, "libs_bridge": libs_bridge,
            "libs_gempa": libs_gempa, "libs_hidrologi": libs_hidrologi,
            "libs_irigasi": libs_irigasi, "libs_bendung": libs_bendung, "libs_jiat": libs_jiat,
            "libs_ahsp": libs_ahsp, "libs_rab_engine": libs_rab_engine,
            "libs_optimizer": libs_optimizer, "libs_research": libs_research,
            "libs_arch": libs_arch, "libs_zoning": libs_zoning, "libs_green": libs_green,
            "libs_pdf": libs_pdf, "libs_export": libs_export,
            "libs_bim_importer": libs_bim_importer
        }
        
        # Inject Geotek jika ada
        if 'libs_geoteknik' in globals(): local_vars['libs_geoteknik'] = libs_geoteknik
        if 'libs_pondasi' in globals(): local_vars['libs_pondasi'] = libs_pondasi
        
        if file_ifc_path: local_vars["file_ifc_user"] = file_ifc_path
        
        exec(code_str, {}, local_vars)
        return True
    except Exception as e:
        st.error(f"⚠️ Eksekusi Kode Gagal: {e}")
        with st.expander("Lihat Kode Error"): st.code(code_str, language='python')
        return False

# ==========================================
# 4. FUNGSI EXPORT DOKUMEN (WORD/EXCEL/PDF)
# ==========================================
def create_docx(text):
    doc = docx.Document()
    doc.add_heading('Laporan ENGINEX', 0)
    for line in text.split('\n'):
        doc.add_paragraph(line)
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

def create_excel(text):
    data = []
    for line in text.split('\n'):
        if "|" in line and "---" not in line:
            row = [c.strip() for c in line.split('|') if c.strip()]
            if row: data.append(row)
    if len(data) < 2: return None
    df = pd.DataFrame(data[1:], columns=data[0])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio) as writer: df.to_excel(writer, index=False)
    bio.seek(0)
    return bio

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    # FPDF standar tidak support Unicode kompleks, kita ganti karakter spesial
    clean_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_text)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. SIDEBAR: KONTROL UTAMA
# ==========================================
if 'backend' not in st.session_state: st.session_state.backend = EnginexBackend()
if 'processed_files' not in st.session_state: st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state: st.session_state.current_expert_active = "👑 The GEMS Grandmaster"

db = st.session_state.backend

with st.sidebar:
    st.title("🏗️ ENGINEX ULTIMATE")
    
    # 1. API KEY
    api_key_input = st.text_input("🔑 Google API Key:", type="password")
    raw_key = api_key_input if api_key_input else st.secrets.get("GOOGLE_API_KEY")
    if not raw_key: st.warning("Butuh API Key."); st.stop()
    genai.configure(api_key=raw_key.strip(), transport="rest")
    
    # 2. PILIH MODEL (FULL LIST UPDATE 2026)
    # Daftar lengkap termasuk Gemini 3, 2.5, Robotics, dll
    AVAILABLE_MODELS = [
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-flash-latest",
        "gemini-3-flash-preview",
        "gemini-2.5-flash-preview",
        "gemini-2.5-flash-lite-preview",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-image",
        "gemini-2.5-computer",   
        "gemini-robotics-er-1.5-preview
        "gemini-exp-1206"
    ]
    model_name = st.selectbox("🧠 Model AI:", AVAILABLE_MODELS, index=0)
    
    # Info Mode (Updated Logic)
    if "3-flash" in model_name:
        st.success("🚀 Mode: NEXT-GEN SPEED (Gemini 3)")
    elif "2.5" in model_name:
        st.info("⚡ Mode: ULTRA EFFICIENT (Gemini 2.5)")
    elif "robotics" in model_name:
        st.warning("🤖 Mode: ROBOTICS SPECIALIST")
    elif "pro" in model_name:
        st.success("🧠 Mode: HIGH REASONING")
    else:
        st.info("🚀 Mode: STANDARD SPEED")
    
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot (Smart Router)", value=True)
    
    st.divider()
    
    # 3. MANAJEMEN PROYEK (OPEN/SAVE)
    st.markdown("### 📂 Proyek")
    col_p1, col_p2 = st.columns(2)
    # Save/Backup
    col_p1.download_button("💾 Backup", db.export_data(), "backup_enginex.json", "application/json")
    # Restore
    uploaded_backup = col_p2.file_uploader("📂 Restore", type=["json"], label_visibility="collapsed")
    if uploaded_backup:
        ok, msg = db.import_data(uploaded_backup)
        if ok: st.success("Restored!"); st.rerun()
    
    # Pilih Proyek Aktif
    projects = db.daftar_proyek()
    mode = st.radio("Mode:", ["Buka Proyek", "Buat Baru"], horizontal=True, label_visibility="collapsed")
    if mode == "Buat Baru":
        nama_proyek = st.text_input("Nama Proyek Baru:", "Proyek-01")
    else:
        nama_proyek = st.selectbox("Pilih Proyek:", projects) if projects else "Default Project"

    st.divider()
    
    # 4. UPLOAD FILE
    st.markdown("### 📎 Upload Data")
    uploaded_files = st.file_uploader("", type=["png","jpg","pdf","xlsx","docx","ifc","py"], accept_multiple_files=True)
    
    if st.button("🧹 Reset Chat"):
        db.clear_chat(nama_proyek, st.session_state.current_expert_active)
        st.rerun()

# ==========================================
# 6. AREA CHAT UTAMA
# ==========================================
st.markdown(f'<div class="main-header">{nama_proyek}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Ahli Aktif: <b>{st.session_state.current_expert_active}</b></div>', unsafe_allow_html=True)

# Tampilkan History
history = db.get_chat_history(nama_proyek, st.session_state.current_expert_active)
for msg in history:
    with st.chat_message(msg['role']): st.markdown(msg['content'])

# Input User
prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")

if prompt:
    # A. Auto-Pilot Logic (Router)
    target_expert = st.session_state.current_expert_active
    if use_auto_pilot:
        with st.status("🧠 Menganalisis kebutuhan...", expanded=False):
            try:
                router = genai.GenerativeModel("gemini-1.5-flash")
                list_ahli = list(gems_persona.keys())
                res = router.generate_content(f"User: '{prompt}'. Siapa ahli paling pas dari: {list_ahli}? Jawab HANYA nama.")
                sug = res.text.strip()
                if sug in list_ahli: 
                    target_expert = sug
                    st.session_state.current_expert_active = sug
            except: pass

    # B. Simpan Chat User
    db.simpan_chat(nama_proyek, target_expert, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)

    # C. Proses Konteks & File
    full_prompt = [prompt]
    file_ifc_obj = None
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.processed_files:
                name = f.name.lower()
                if name.endswith(('.png','.jpg')): 
                    full_prompt.append(Image.open(f))
                    with st.chat_message("user"): st.image(f, width=200)
                elif name.endswith('.pdf'):
                    reader = PyPDF2.PdfReader(f)
                    txt = "\n".join([p.extract_text() for p in reader.pages])
                    full_prompt[0] += f"\n\n[FILE: {f.name}]\n{txt}"
                elif name.endswith('.ifc'):
                    file_ifc_obj = f # Simpan untuk engine
                    with st.chat_message("user"): st.caption(f"🏗️ BIM Model: {f.name}")
                st.session_state.processed_files.add(f.name)

    # D. Generate Jawaban AI
    with st.chat_message("assistant"):
        with st.spinner(f"{target_expert} sedang bekerja..."):
            try:
                # Instruksi Coding
                SYS = gems_persona[target_expert] + """
                \n[ATURAN CODE]:
                1. Jika butuh hitungan/grafik, TULIS KODE PYTHON (```python).
                2. Gunakan library `libs_...` yang tersedia.
                3. Tampilkan grafik: `st.pyplot(plt.gcf())`.
                4. Tampilkan tabel: `st.dataframe(df)`.
                5. Jika diminta file DXF, gunakan `libs_irigasi.generate_dxf_script()` dan tampilkan tombol download.
                """
                
                model = genai.GenerativeModel(model_name, system_instruction=SYS)
                chat = model.start_chat(history=[{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt])
                
                response = chat.send_message(full_prompt)
                st.markdown(response.text)
                db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                
                # E. Eksekusi Kode Python (Plotting & DXF)
                code_blocks = re.findall(r"```python(.*?)```", response.text, re.DOTALL)
                for code in code_blocks:
                    st.markdown("---")
                    st.caption("⚙️ **Engine Output:**")
                    execute_generated_code(code, file_ifc_path=file_ifc_obj)
                
                # F. EXPORT BUTTONS (Word, Excel, PDF)
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                
                # PDF Export
                try:
                    pdf_bytes = create_pdf(response.text)
                    c1.download_button("📄 Export PDF", pdf_bytes, "Laporan.pdf", "application/pdf")
                except: c1.caption("PDF N/A")
                
                # Word Export
                doc_bytes = create_docx(response.text)
                if doc_bytes: c2.download_button("📝 Export Word", doc_bytes, "Laporan.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                
                # Excel Export
                xls_bytes = create_excel(response.text)
                if xls_bytes: c3.download_button("📊 Export Excel", xls_bytes, "Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            except Exception as e:
                st.error(f"Error: {e}")

