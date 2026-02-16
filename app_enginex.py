import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
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
# REGISTRASI MODUL KE SYSTEM
# ==========================================
# Tujuannya agar AI bisa memanggil 'import libs_sni' tanpa path panjang
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
# 2. KONFIGURASI HALAMAN & SECURITY
# ==========================================
st.set_page_config(
    page_title="ENGINEX Ultimate", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# [SECURITY FIX] Style CSS dipisah agar aman.
st.markdown("""
<style>
    [data-testid="stSidebar"] {background-color: #F8FAFC; border-right: 1px solid #E2E8F0;}
    .stChatInput textarea {font-size: 16px !important;}
    .stDownloadButton button {width: 100%; border-radius: 6px; font-weight: 600;}
    
    /* Sembunyikan Elemen Default Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Styling Expander agar lebih rapi */
    .streamlit-expanderHeader {
        font-size: 14px;
        color: #64748B;
        background-color: #F1F5F9;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. ENGINE EKSEKUSI KODE (SHARED MEMORY)
# ==========================================
if 'shared_execution_vars' not in st.session_state:
    st.session_state.shared_execution_vars = {}

def execute_generated_code(code_str, file_ifc_path=None):
    """
    Menjalankan kode Python AI dengan Memori Persisten.
    """
    try:
        # 1. Ambil variabel dari memori sebelumnya
        local_vars = st.session_state.shared_execution_vars.copy()
        
        # 2. Suntikkan Library Wajib (Termasuk Plotly)
        library_kits = {
            "pd": pd, "np": np, "plt": plt, "st": st, "px": px, "go": go,
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
            
        local_vars.update(library_kits)
        
        # 3. Suntikkan File IFC jika ada
        if file_ifc_path: 
            local_vars["file_ifc_user"] = file_ifc_path
        
        # 4. EKSEKUSI KODE
        # [SECURITY NOTE] exec() dijalankan di environment terkontrol
        exec(code_str, local_vars)
        
        # 5. SIMPAN HASIL KE MEMORI
        for k, v in local_vars.items():
            if k not in library_kits and not k.startswith('__') and not isinstance(v, types.ModuleType):
                st.session_state.shared_execution_vars[k] = v
                
        return True
    except Exception as e:
        # Suppress error visual di history agar bersih
        # st.error(f"Runtime Error: {e}") 
        return False

# ==========================================
# 4. FUNGSI EXPORT DOKUMEN (CLEAN REPORT)
# ==========================================
def clean_text_for_report(text):
    """
    Membersihkan teks dari blok kode Python sebelum dicetak ke PDF/Word.
    Agar laporan terlihat profesional (No Leaking Code).
    """
    # Hapus blok kode ```python ... ```
    clean = re.sub(r"```python.*?```", "", text, flags=re.DOTALL)
    # Hapus blok kode ``` ... ``` umum
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    # Rapikan baris kosong berlebih
    clean = re.sub(r'\n\s*\n', '\n\n', clean)
    return clean.strip()

def create_docx(text):
    try:
        doc = docx.Document()
        doc.add_heading('Laporan ENGINEX', 0)
        
        # [FIX] Bersihkan kode sebelum masuk Word
        clean_content = clean_text_for_report(text)
        
        for line in clean_content.split('\n'):
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

# [INTEGRASI PDF CANGGIH]
try:
    import libs_pdf
except ImportError:
    libs_pdf = None

def create_pdf(text_content):
    """
    Fungsi Wrapper untuk memanggil Generator Laporan.
    """
    if libs_pdf:
        try:
            # Panggil fungsi 'create_tabg_report'
            pdf_bytes = libs_pdf.create_tabg_report(st.session_state, project_name="Proyek SmartBIM")
            return pdf_bytes
        except Exception as e:
            # Fallback ke PDF sederhana
            from fpdf import FPDF
            
            # [FIX] Bersihkan kode sebelum masuk PDF Sederhana
            clean_content = clean_text_for_report(text_content)
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 6, clean_content)
            return pdf.output(dest='S').encode('latin-1')
    else:
        return None

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
    
    # 2. MODEL SELECTION
    AVAILABLE_MODELS = [
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-image",
        "gemini-2.5-flash-preview",
        "gemini-3-flash-preview",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "models/gemini-robotics-er-1-preview",
    ]
    model_name = st.selectbox("🧠 Model AI:", AVAILABLE_MODELS, index=0)
    
    # 3. MODE PERSONA
    st.markdown("### 🎭 Mode Persona")
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot (Smart Router)", value=True)

    daftar_ahli = get_persona_list()
    
    if use_auto_pilot:
        st.info(f"📍 Ahli Aktif: **{st.session_state.current_expert_active}**")
        st.caption("AI otomatis memilih ahli sesuai pertanyaan.")
    else:
        selected_expert = st.selectbox("👨‍💼 Pilih Spesialis Manual:", daftar_ahli, index=0)
        st.session_state.current_expert_active = selected_expert
    
    # 4. PARAMETER GEMPA (SNI 1726:2019)
    with st.expander("⚙️ Parameter Gempa (SNI 1726:2019)"):
        st.caption("Input Presisi (4 Desimal)")
        ss_input = st.number_input("Ss (Batuan Dasar)", value=0.6000, format="%.4f", step=0.0001)
        s1_input = st.number_input("S1 (Periode 1 Detik)", value=0.2500, format="%.4f", step=0.0001)
        
        if 'shared_execution_vars' not in st.session_state:
            st.session_state.shared_execution_vars = {}
            
        st.session_state.shared_execution_vars['Ss_user'] = ss_input
        st.session_state.shared_execution_vars['S1_user'] = s1_input
        st.info(f"Setting Aktif: Ss={ss_input:.4f}, S1={s1_input:.4f}")

    st.divider()
      
    # 5. MANAJEMEN PROYEK
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
    
    # 6. UPLOAD FILE
    st.markdown("### 📎 Upload Data")
    uploaded_files = st.file_uploader("", type=["png","jpg","pdf","xlsx","docx","ifc","py"], accept_multiple_files=True)
    
    if st.button("🧹 Reset Chat"):
        db.clear_chat(nama_proyek, st.session_state.current_expert_active)
        st.session_state.processed_files.clear()
        st.session_state.shared_execution_vars = {}
        st.rerun()

# ==========================================
# 6. AREA CHAT UTAMA (HYBRID PROFESSIONAL)
# ==========================================
st.title(nama_proyek)
st.caption(f"Ahli Aktif: {st.session_state.current_expert_active}")

# Tampilkan History
history = db.get_chat_history(nama_proyek, st.session_state.current_expert_active)

# Counter unik untuk tombol download agar tidak bentrok (Streamlit Key Issue)
download_btn_counter = 0

for msg in history:
    with st.chat_message(msg['role']):
        content = msg['content']
        
        # [UI FIX] PISAHKAN TEKS DAN KODE
        # Teks ditampilkan biasa, Kode disembunyikan di Expander
        parts = re.split(r"(```python.*?```)", content, flags=re.DOTALL)
        
        for part in parts:
            if part.startswith("```python"):
                download_btn_counter += 1
                
                # Bersihkan string kode
                code_content = part.replace("```python", "").replace("```", "").strip()
                
                # 1. TAMPILKAN EXPANDER (PROFESIONAL)
                with st.expander("🛠️ Lihat Detail Teknis (Engine Output)"):
                    st.code(code_content, language='python')
                    
                    # 2. [FITUR BARU] TOMBOL DOWNLOAD SCRIPT
                    # Key harus unik agar tidak crash
                    unique_key = f"dl_btn_{download_btn_counter}"
                    st.download_button(
                        label="📥 Download Script (.py)",
                        data=code_content,
                        file_name=f"enginex_result_{download_btn_counter}.py",
                        mime="text/x-python",
                        key=unique_key
                    )
                
                # 3. JALANKAN KODE (TAMPILKAN HASIL VISUAL)
                execute_generated_code(code_content)
            else:
                # Ini adalah Teks Narasi -> Tampilkan
                st.markdown(part)

# Input User
prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")

if prompt:
    # A. AUTO-PILOT LOGIC
    target_expert = st.session_state.current_expert_active
    
    if use_auto_pilot:
        with st.status("🧠 Menganalisis kebutuhan...", expanded=False):
            try:
                router = genai.GenerativeModel("gemini-1.5-flash")
                list_ahli = get_persona_list()
                router_prompt = f"User bertanya: '{prompt}'. Siapa ahli paling pas dari daftar ini: {list_ahli}? Jawab HANYA nama ahlinya persis."
                res = router.generate_content(router_prompt)
                sug = res.text.strip()
                if any(sug in ahli for ahli in list_ahli): 
                    target_expert = sug
                    st.session_state.current_expert_active = sug
            except: pass
    else:
        target_expert = st.session_state.current_expert_active

    # B. SIMPAN USER CHAT
    db.simpan_chat(nama_proyek, target_expert, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)

    # C. SIAPKAN KONTEKS & FILE
    full_prompt = [prompt]
    file_ifc_path = None
    
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.processed_files:
                name = f.name.lower()
                
                if name.endswith(('.png','.jpg','.jpeg')): 
                    full_prompt.append(Image.open(f))
                    with st.chat_message("user"): st.image(f, width=200)
                
                elif name.endswith('.pdf'):
                    reader = PyPDF2.PdfReader(f)
                    txt = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                    full_prompt[0] += f"\n\n[FILE CONTENT: {f.name}]\n{txt}"
                
                elif name.endswith('.ifc'):
                    with open(f.name, "wb") as buffer: buffer.write(f.getbuffer())
                    file_ifc_path = f.name
                    full_prompt[0] += f"\n\n[SYSTEM]: User mengupload IFC di '{f.name}'. Gunakan `libs_bim_importer`."
                    with st.chat_message("user"): st.caption(f"🏗️ BIM Model: {f.name}")
                
                st.session_state.processed_files.add(f.name)

    # D. GENERATE JAWABAN
    with st.chat_message("assistant"):
        with st.spinner(f"{target_expert} sedang bekerja..."):
            try:
                from core.persona import gems_persona
                persona_instr = gems_persona.get(target_expert, gems_persona["👑 The GEMS Grandmaster"])
                
                # [UPDATE SYSTEM INSTRUCTION] - MEMAKSA AI JADI PROFESIONAL
                SYS = persona_instr + """
                \n[ATURAN TAMPILAN WAJIB (STRICT)]:
                1. KODE PYTHON: Wajib ditulis dalam blok ```python.
                2. FORMAT UANG: Gunakan format Indonesia (Rp 1.000.000), JANGAN scientific (1e6).
                3. GRAFIK: Gunakan library 'plotly' (import plotly.express as px) agar interaktif.
                4. TABEL: Gunakan st.dataframe(df) untuk data.
                5. BAHASA: Profesional, Engineer-to-Client.
                """
                
                model = genai.GenerativeModel(model_name, system_instruction=SYS)
                chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                
                chat = model.start_chat(history=chat_hist)
                response = chat.send_message(full_prompt)
                
                # [UI DISPLAY] Tampilkan hasil dengan Hybrid Mode
                parts = re.split(r"(```python.*?```)", response.text, flags=re.DOTALL)
                
                # Offset counter untuk response baru agar tidak bentrok dengan history
                download_btn_counter_new = 9000 
                
                for part in parts:
                    if part.startswith("```python"):
                        download_btn_counter_new += 1
                        code_content = part.replace("```python", "").replace("```", "").strip()
                        
                        # Tampilkan Expander + Tombol Download
                        with st.expander("🛠️ Lihat Detail Teknis (Engine Output)"):
                            st.code(code_content, language='python')
                            
                            unique_key_new = f"dl_btn_new_{download_btn_counter_new}"
                            st.download_button(
                                label="📥 Download Script (.py)",
                                data=code_content,
                                file_name=f"enginex_result_{download_btn_counter_new}.py",
                                mime="text/x-python",
                                key=unique_key_new
                            )
                        
                        # Eksekusi Visual
                        execute_generated_code(code_content, file_ifc_path=file_ifc_path)
                    else:
                        st.markdown(part)

                db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                
                # F. EXPORT
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                try:
                    pdf_bytes = create_pdf(response.text)
                    if pdf_bytes: c1.download_button("📄 PDF (Laporan Resmi)", pdf_bytes, "Laporan_EnginEX.pdf")
                except: pass
                
                doc_bytes = create_docx(response.text)
                if doc_bytes: c2.download_button("📝 Word (Editable)", doc_bytes, "Laporan.docx")
                
                xls_bytes = create_excel(response.text)
                if xls_bytes: c3.download_button("📊 Excel (Data)", xls_bytes, "Data.xlsx")

            except Exception as e:
                st.error(f"Error: {e}")


