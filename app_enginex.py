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
import sys
from fpdf import FPDF 

# ==========================================
# 1. IMPORT LIBRARY ENGINEERING (MODULAR)
# ==========================================
# Kita gunakan try-except agar aplikasi tidak 'crash' jika ada file yang belum terupload,
# tapi tetap memberitahu user apa yang kurang.

try:
    # A. Core Modules
    from core.backend_enginex import EnginexBackend
    from core.persona import gems_persona, get_persona_list

    # B. Engineering Modules
    # Struktur
    from modules.struktur import libs_sni, libs_baja, libs_bridge, libs_gempa
    
    # Water Resources
    from modules.water import libs_hidrologi, libs_irigasi, libs_jiat, libs_bendung
    
    # Cost & Management
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research
    
    # Architecture & Environment
    from modules.arch import libs_arch, libs_zoning, libs_green
    
    # Utils
    from modules.utils import libs_pdf, libs_export, libs_bim_importer
    
    # Optional Modules (Geoteknik)
    try: 
        from modules.geotek import libs_geoteknik, libs_pondasi
        has_geotek = True
    except ImportError: 
        has_geotek = False

except ImportError as e:
    st.error(f"⚠️ **CRITICAL SYSTEM ERROR**")
    st.write(f"Gagal memuat modul. Pesan Error: `{e}`")
    st.info("Saran: Pastikan struktur folder `modules/` di GitHub sudah lengkap dengan file `__init__.py`.")
    st.stop()

# ==========================================
# [SAFETY NET] REGISTRASI MODUL KE SYSTEM
# ==========================================
# Bagian ini PENTING agar antar-library bisa saling mengenali 
# meskipun dijalankan di lingkungan Streamlit Cloud yang unik.

sys.modules['libs_sni'] = libs_sni
sys.modules['libs_baja'] = libs_baja
sys.modules['libs_bridge'] = libs_bridge
sys.modules['libs_gempa'] = libs_gempa

sys.modules['libs_hidrologi'] = libs_hidrologi
sys.modules['libs_irigasi'] = libs_irigasi
sys.modules['libs_jiat'] = libs_jiat
sys.modules['libs_bendung'] = libs_bendung

sys.modules['libs_ahsp'] = libs_ahsp
sys.modules['libs_rab_engine'] = libs_rab_engine
sys.modules['libs_optimizer'] = libs_optimizer
sys.modules['libs_research'] = libs_research

sys.modules['libs_arch'] = libs_arch
sys.modules['libs_zoning'] = libs_zoning
sys.modules['libs_green'] = libs_green

sys.modules['libs_pdf'] = libs_pdf
sys.modules['libs_export'] = libs_export
sys.modules['libs_bim_importer'] = libs_bim_importer

if has_geotek:
    sys.modules['libs_geoteknik'] = libs_geoteknik
    sys.modules['libs_pondasi'] = libs_pondasi

# ==========================================
# 2. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="ENGINEX Ultimate", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan yang bersih dan profesional
st.markdown("""
<style>
    .main-header {font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 5px;}
    .sub-header {font-size: 14px; color: #64748B; margin-bottom: 20px;}
    [data-testid="stSidebar"] {background-color: #F8FAFC; border-right: 1px solid #E2E8F0;}
    .stChatInput textarea {font-size: 16px !important;}
    .stDownloadButton button {width: 100%; border-radius: 6px; font-weight: 600;}
    .success-box {padding:10px; background-color:#d4edda; color:#155724; border-radius:5px; margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. ENGINE EKSEKUSI KODE (LOGIC INJECTION)
# ==========================================
def execute_generated_code(code_str, file_ifc_path=None):
    """
    Fungsi ini mengeksekusi kode Python yang dibuat oleh AI.
    Kita menyuntikkan (inject) semua library engineering ke dalamnya
    agar AI bisa memanggil 'libs_sni.hitung_balok()' dll.
    """
    try:
        local_vars = {
            "pd": pd, "np": np, "plt": plt, "st": st,
            
            # Struktur
            "libs_sni": libs_sni, 
            "libs_baja": libs_baja, 
            "libs_bridge": libs_bridge,
            "libs_gempa": libs_gempa, 
            
            # Water
            "libs_hidrologi": libs_hidrologi,
            "libs_irigasi": libs_irigasi, 
            "libs_bendung": libs_bendung, 
            "libs_jiat": libs_jiat,
            
            # Cost
            "libs_ahsp": libs_ahsp, 
            "libs_rab_engine": libs_rab_engine,
            "libs_optimizer": libs_optimizer, 
            "libs_research": libs_research,
            
            # Arch & Utils
            "libs_arch": libs_arch, 
            "libs_zoning": libs_zoning, 
            "libs_green": libs_green,
            "libs_pdf": libs_pdf, 
            "libs_export": libs_export,
            "libs_bim_importer": libs_bim_importer
        }
        
        # Inject Geotek jika tersedia
        if has_geotek:
            local_vars['libs_geoteknik'] = libs_geoteknik
            local_vars['libs_pondasi'] = libs_pondasi
        
        # Inject IFC File Path untuk modul BIM
        if file_ifc_path: 
            local_vars["file_ifc_user"] = file_ifc_path
        
        # Eksekusi Kode
        exec(code_str, {}, local_vars)
        return True
    except Exception as e:
        st.error(f"⚠️ Gagal Eksekusi Kode: {e}")
        with st.expander("🔍 Lihat Kode Error"): 
            st.code(code_str, language='python')
        return False

# ==========================================
# 4. FUNGSI EXPORT DOKUMEN (PDF/WORD/EXCEL)
# ==========================================
def create_docx(text):
    try:
        doc = docx.Document()
        doc.add_heading('Laporan ENGINEX', 0)
        for line in text.split('\n'):
            clean = line.strip()
            if clean: doc.add_paragraph(clean)
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        return bio
    except: return None

def create_excel(text):
    try:
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
    except: return None

def create_pdf(text):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        # Encode ke latin-1 untuk kompatibilitas FPDF standar
        clean_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# ==========================================
# 5. SIDEBAR & SETUP SESI
# ==========================================
# Inisialisasi Database & Session State
if 'backend' not in st.session_state: 
    st.session_state.backend = EnginexBackend()
if 'processed_files' not in st.session_state: 
    st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state: 
    st.session_state.current_expert_active = "👑 The GEMS Grandmaster"

db = st.session_state.backend

with st.sidebar:
    st.title("🏗️ ENGINEX ULTIMATE")
    
    # --- 1. API KEY SETUP ---
    api_key_input = st.text_input("🔑 Google API Key:", type="password")
    raw_key = api_key_input if api_key_input else st.secrets.get("GOOGLE_API_KEY")
    
    if not raw_key: 
        st.warning("⚠️ Masukkan API Key Google AI Studio.")
        st.stop()
    
    try:
        genai.configure(api_key=raw_key.strip(), transport="rest")
    except Exception as e:
        st.error(f"API Config Error: {e}")
    
    # --- 2. MODEL SELECTION (UPDATE 2026) ---
    # Daftar model lengkap sesuai permintaan user
    AVAILABLE_MODELS = [
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-image",
        "gemini-2.5-flash-preview",
        "gemini-2.5-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-robotics-er-1.5-preview",
        "gemini-2.5-computer",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    
    model_name = st.selectbox("🧠 Model AI:", AVAILABLE_MODELS, index=0)
    
    # Indikator Mode Berdasarkan Model
    if "3-flash" in model_name:
        st.success("🚀 Mode: NEXT-GEN (Gemini 3.0)")
    elif "2.5" in model_name:
        st.info("⚡ Mode: ULTRA EFFICIENT (Gemini 2.5)")
    elif "robotics" in model_name:
        st.warning("🤖 Mode: ROBOTICS SPECIALIST")
    elif "computer" in model_name:
        st.warning("💻 Mode: COMPUTER USE")
    else:
        st.caption("Mode: Standard Production")
    
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot (Smart Router)", value=True)
    
    st.divider()
    
    # --- 3. MANAJEMEN PROYEK ---
    st.markdown("### 📂 Proyek")
    col_p1, col_p2 = st.columns(2)
    # Tombol Backup & Restore
    col_p1.download_button("💾 Backup", db.export_data(), "backup_enginex.json", "application/json")
    uploaded_backup = col_p2.file_uploader("📂 Restore", type=["json"], label_visibility="collapsed")
    if uploaded_backup:
        ok, msg = db.import_data(uploaded_backup)
        if ok: st.success("Data Pulih!"); st.rerun()
    
    # Pilihan Proyek
    projects = db.daftar_proyek()
    mode = st.radio("Mode:", ["Buka Proyek", "Buat Baru"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Buat Baru":
        nama_proyek = st.text_input("Nama Proyek Baru:", "Proyek-Baru-01")
    else:
        nama_proyek = st.selectbox("Pilih Proyek:", projects) if projects else "Default Project"

    st.divider()
    
    # --- 4. UPLOAD DATA ---
    st.markdown("### 📎 Upload Input")
    uploaded_files = st.file_uploader("", type=["png","jpg","pdf","xlsx","docx","ifc","py"], accept_multiple_files=True)
    
    if st.button("🧹 Reset Chat"):
        db.clear_chat(nama_proyek, st.session_state.current_expert_active)
        st.session_state.processed_files.clear()
        st.rerun()

# ==========================================
# 6. AREA CHAT UTAMA
# ==========================================
st.markdown(f'<div class="main-header">{nama_proyek}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Ahli Aktif: <b>{st.session_state.current_expert_active}</b></div>', unsafe_allow_html=True)

# Tampilkan Riwayat Chat
history = db.get_chat_history(nama_proyek, st.session_state.current_expert_active)
for msg in history:
    with st.chat_message(msg['role']): st.markdown(msg['content'])

# Input Prompt User
prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")

if prompt:
    # A. LOGIKA AUTO-PILOT (ROUTER)
    target_expert = st.session_state.current_expert_active
    if use_auto_pilot:
        with st.status("🧠 Menganalisis kebutuhan...", expanded=False):
            try:
                # Gunakan model ringan untuk routing
                router = genai.GenerativeModel("gemini-1.5-flash")
                list_ahli = list(gems_persona.keys())
                router_prompt = f"User bertanya: '{prompt}'. Siapa ahli paling tepat dari daftar ini: {list_ahli}? Jawab HANYA nama ahlinya persis."
                res = router.generate_content(router_prompt)
                sug = res.text.strip()
                if sug in list_ahli: 
                    target_expert = sug
                    st.session_state.current_expert_active = sug
            except: pass

    # B. SIMPAN CHAT USER
    db.simpan_chat(nama_proyek, target_expert, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)

    # C. SIAPKAN KONTEKS & FILE
    full_prompt = [prompt]
    file_ifc_obj = None
    
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.processed_files:
                name = f.name.lower()
                # Proses Gambar
                if name.endswith(('.png','.jpg','.jpeg')): 
                    full_prompt.append(Image.open(f))
                    with st.chat_message("user"): st.image(f, width=200)
                # Proses PDF
                elif name.endswith('.pdf'):
                    reader = PyPDF2.PdfReader(f)
                    txt = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                    full_prompt[0] += f"\n\n[FILE CONTENT: {f.name}]\n{txt}"
                # Proses IFC (Untuk BIM Engine)
                elif name.endswith('.ifc'):
                    file_ifc_obj = f 
                    with st.chat_message("user"): st.caption(f"🏗️ BIM Model: {f.name} siap diproses")
                # Tandai sudah diproses
                st.session_state.processed_files.add(f.name)

    # D. GENERATE JAWABAN AI
    with st.chat_message("assistant"):
        with st.spinner(f"{target_expert} sedang bekerja..."):
            try:
                # Tambahkan Instruksi Coding ke System Prompt
                SYS_PROMPT = gems_persona[target_expert] + """
                \n[INSTRUKSI CODING WAJIB]:
                1. Jika user meminta hitungan, tabel, atau grafik, TULIS KODE PYTHON (```python).
                2. Gunakan library custom yang tersedia: `libs_sni`, `libs_irigasi`, `libs_hidrologi`, `libs_rab_engine`, `libs_ahsp`.
                3. Untuk menampilkan grafik, akhiri kode dengan: `st.pyplot(plt.gcf())`.
                4. Untuk menampilkan tabel dataframe, akhiri kode dengan: `st.dataframe(df)`.
                5. Jika user meminta file DXF, gunakan `libs_irigasi.generate_dxf_script()` dan tampilkan tombol download.
                """
                
                # Inisialisasi Model
                model = genai.GenerativeModel(
                    model_name, 
                    system_instruction=SYS_PROMPT
                )
                
                # Build History Chat untuk Konteks
                chat_hist = []
                for h in history:
                    if h['content'] != prompt:
                        role_api = "user" if h['role']=="user" else "model"
                        chat_hist.append({"role": role_api, "parts": [h['content']]})
                
                chat_session = model.start_chat(history=chat_hist)
                response = chat_session.send_message(full_prompt)
                
                # Tampilkan Jawaban Teks
                st.markdown(response.text)
                db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                
                # E. EKSEKUSI KODE PYTHON (JIKA ADA)
                code_blocks = re.findall(r"```python(.*?)```", response.text, re.DOTALL)
                for code in code_blocks:
                    st.markdown("---")
                    st.caption("⚙️ **Engine Output:**")
                    # Jalankan kode dengan akses ke library
                    execute_generated_code(code, file_ifc_path=file_ifc_obj)
                
                # F. TOMBOL EXPORT (PDF/WORD/EXCEL)
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                
                # PDF
                try:
                    pdf_bytes = create_pdf(response.text)
                    if pdf_bytes: c1.download_button("📄 Export PDF", pdf_bytes, "Laporan.pdf", "application/pdf")
                except: pass
                
                # Word
                doc_bytes = create_docx(response.text)
                if doc_bytes: c2.download_button("📝 Export Word", doc_bytes, "Laporan.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                
                # Excel
                xls_bytes = create_excel(response.text)
                if xls_bytes: c3.download_button("📊 Export Excel", xls_bytes, "Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            except Exception as e:
                st.error(f"⚠️ Error: {e}")
                st.info("Jika error terkait model (404), coba ganti Model AI di sidebar.")

