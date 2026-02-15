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
import types
from fpdf import FPDF 

# ==========================================
# 1. IMPORT LIBRARY ENGINEERING (MODULAR)
# ==========================================
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
    st.write(f"Gagal memuat modul engineering. Pesan Error: `{e}`")
    st.stop()

# ==========================================
# [FIX 1] REGISTRASI MODUL KE SYSTEM
# ==========================================
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
# 3. ENGINE EKSEKUSI KODE (SHARED MEMORY)
# ==========================================
# [FIX 2] Shared Memory Initialization
# Inilah kunci agar 'np' tidak hilang antar blok kode
if 'shared_execution_vars' not in st.session_state:
    st.session_state.shared_execution_vars = {}

def execute_generated_code(code_str, file_ifc_path=None):
    """
    Menjalankan kode Python AI dengan Memori Persisten.
    """
    try:
        # 1. Ambil variabel dari memori sebelumnya (agar L_bentang, Mu, dll tersimpan)
        local_vars = st.session_state.shared_execution_vars.copy()
        
        # 2. Suntikkan Library Wajib (Agar 'np' selalu ada meskipun AI lupa import)
        library_kits = {
            "pd": pd, "np": np, "plt": plt, "st": st,
            
            # Modules Dictionary
            "libs_sni": libs_sni, "libs_baja": libs_baja, "libs_bridge": libs_bridge,
            "libs_gempa": libs_gempa, "libs_hidrologi": libs_hidrologi,
            "libs_irigasi": libs_irigasi, "libs_bendung": libs_bendung, "libs_jiat": libs_jiat,
            "libs_ahsp": libs_ahsp, "libs_rab_engine": libs_rab_engine,
            "libs_optimizer": libs_optimizer, "libs_research": libs_research,
            "libs_arch": libs_arch, "libs_zoning": libs_zoning, "libs_green": libs_green,
            "libs_pdf": libs_pdf, "libs_export": libs_export,
            "libs_bim_importer": libs_bim_importer
        }
        
        if has_geotek:
            library_kits['libs_geoteknik'] = libs_geoteknik
            library_kits['libs_pondasi'] = libs_pondasi
            
        # Update local_vars dengan library kits
        local_vars.update(library_kits)
        
        # 3. Suntikkan File IFC jika ada
        if file_ifc_path: 
            local_vars["file_ifc_user"] = file_ifc_path
        
        # 4. EKSEKUSI KODE
        # Gunakan local_vars sebagai globals dan locals agar persistensi maksimal
        exec(code_str, local_vars)
        
        # 5. SIMPAN HASIL KE MEMORI (Kecuali Modul/Library/Fungsi Bawaan)
        for k, v in local_vars.items():
            # Filter agar memori tidak penuh sampah
            if k not in library_kits and not k.startswith('__') and not isinstance(v, types.ModuleType):
                st.session_state.shared_execution_vars[k] = v
                
        return True
    except Exception as e:
        st.error(f"⚠️ Gagal Eksekusi Kode: {e}")
        with st.expander("🔍 Lihat Kode Error"): 
            st.code(code_str, language='python')
        return False

# ==========================================
# 4. FUNGSI EXPORT DOKUMEN
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
        clean_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_text)
        return pdf.output(dest='S').encode('latin-1')
    except: return None

# ==========================================
# 5. SIDEBAR & SETUP
# ==========================================
if 'backend' not in st.session_state: 
    st.session_state.backend = EnginexBackend()
if 'processed_files' not in st.session_state: 
    st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state: 
    st.session_state.current_expert_active = "👑 The GEMS Grandmaster"

db = st.session_state.backend

with st.sidebar:
    st.title("🏗️ ENGINEX ULTIMATE")
    
    # 1. API KEY
    api_key_input = st.text_input("🔑 Google API Key:", type="password")
    raw_key = api_key_input if api_key_input else st.secrets.get("GOOGLE_API_KEY")
    
    if not raw_key: 
        st.warning("⚠️ Masukkan API Key.")
        st.stop()
    
    try:
        genai.configure(api_key=raw_key.strip(), transport="rest")
    except Exception as e:
        st.error(f"API Error: {e}")
    
    # 2. MODEL SELECTION (SESUAI SCREENSHOT)
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
    
    # Info Mode
    if "3-flash" in model_name: st.success("🚀 Mode: NEXT-GEN (Gemini 3)")
    elif "2.5" in model_name: st.info("⚡ Mode: ULTRA EFFICIENT")
    elif "robotics" in model_name: st.warning("🤖 Mode: ROBOTICS")
    else: st.caption("Mode: Standard")
    
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot (Smart Router)", value=True)
    
    st.divider()
    
    # 3. MANAJEMEN PROYEK
    st.markdown("### 📂 Proyek")
    col_p1, col_p2 = st.columns(2)
    col_p1.download_button("💾 Backup", db.export_data(), "backup_enginex.json", "application/json")
    uploaded_backup = col_p2.file_uploader("📂 Restore", type=["json"], label_visibility="collapsed")
    if uploaded_backup:
        ok, msg = db.import_data(uploaded_backup)
        if ok: st.success("Data Pulih!"); st.rerun()
    
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
        # Reset Chat dan Memori Variabel
        db.clear_chat(nama_proyek, st.session_state.current_expert_active)
        st.session_state.processed_files.clear()
        st.session_state.shared_execution_vars = {} # Reset memori hitungan
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
    # A. AUTO-PILOT
    target_expert = st.session_state.current_expert_active
    if use_auto_pilot:
        with st.status("🧠 Menganalisis kebutuhan...", expanded=False):
            try:
                # Gunakan model ringan untuk routing
                router = genai.GenerativeModel("gemini-1.5-flash")
                list_ahli = list(gems_persona.keys())
                router_prompt = f"User bertanya: '{prompt}'. Siapa ahli paling pas dari: {list_ahli}? Jawab HANYA nama."
                sug = res.text.strip()
                if sug in list_ahli: 
                    target_expert = sug
                    st.session_state.current_expert_active = sug
            except: pass

    # B. SIMPAN USER CHAT
    db.simpan_chat(nama_proyek, target_expert, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)


    # C. SIAPKAN KONTEKS & FILE
    full_prompt = [prompt]
    file_ifc_path = None # Variabel penampung path
    
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
                
                # [UPDATE] Proses IFC (Simpan ke Temp agar bisa dibaca ifcopenshell)
                elif name.endswith('.ifc'):
                    # Simpan file fisik sementara
                    with open(f.name, "wb") as buffer:
                        buffer.write(f.getbuffer())
                    
                    file_ifc_path = f.name # Simpan path-nya
                    
                    # Beritahu AI bahwa ada file IFC
                    full_prompt[0] += f"\n\n[SYSTEM]: User mengupload file BIM IFC di path '{f.name}'. Gunakan `libs_bim_importer` untuk membacanya."
                    
                    with st.chat_message("user"): 
                        st.caption(f"🏗️ BIM Model: {f.name} (Uploaded & Ready)")
                
                # Tandai sudah diproses
                st.session_state.processed_files.add(f.name)
    
    # D. GENERATE JAWABAN AI
    with st.chat_message("assistant"):
        with st.spinner(f"{target_expert} sedang bekerja..."):
            try:
                # Instruksi Coding Wajib
                SYS = gems_persona[target_expert] + """
                \n[INSTRUKSI CODING WAJIB]:
                1. Jika butuh hitungan/grafik, TULIS KODE PYTHON (```python).
                2. Gunakan library custom: `libs_sni`, `libs_irigasi`, `libs_hidrologi`, `libs_rab_engine`, `libs_optimizer`.
                3. Import library di dalam kode: `import libs_irigasi`, dll.
                4. Tampilkan grafik: `st.pyplot(plt.gcf())`.
                5. Tampilkan tabel: `st.dataframe(df)`.
                6. Variabel Anda tersimpan antar blok kode.
                """
                
                model = genai.GenerativeModel(model_name, system_instruction=SYS)
                chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                
                chat = model.start_chat(history=chat_hist)
                response = chat.send_message(full_prompt)
                
                st.markdown(response.text)
                db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                
                # E. EKSEKUSI KODE
                code_blocks = re.findall(r"```python(.*?)```", response.text, re.DOTALL)
                for code in code_blocks:
                    st.markdown("---")
                    st.caption("⚙️ **Engine Output:**")
                    execute_generated_code(code, file_ifc_path=file_ifc_obj)
                
                # F. EXPORT
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                try:
                    pdf_bytes = create_pdf(response.text)
                    if pdf_bytes: c1.download_button("📄 Export PDF", pdf_bytes, "Laporan.pdf", "application/pdf")
                except: pass
                
                doc_bytes = create_docx(response.text)
                if doc_bytes: c2.download_button("📝 Export Word", doc_bytes, "Laporan.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                
                xls_bytes = create_excel(response.text)
                if xls_bytes: c3.download_button("📊 Export Excel", xls_bytes, "Data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            except Exception as e:
                st.error(f"Error: {e}")

