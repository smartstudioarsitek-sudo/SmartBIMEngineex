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
import time  # Ditambahkan untuk fitur reload (Open Project)
from fpdf import FPDF 

# ==========================================
# 0. KONFIGURASI KEAMANAN & ENVIRONMENT (AUDIT FIX)
# ==========================================
def get_api_key():
    """
    Mengambil API Key dengan aman. Prioritas:
    1. st.secrets (untuk Cloud/Deploy)
    2. Environment Variable
    3. Input Manual (Fallback sementara)
    """
    try:
        return st.secrets["GOOGLE_API_KEY"]
    except (FileNotFoundError, KeyError):
        return os.environ.get("GOOGLE_API_KEY", "")

# ==========================================
# 1. IMPORT LIBRARY ENGINEERING (MODULAR)
# ==========================================
try:
    # A. Core Modules
    from core.backend_enginex import EnginexBackend
    from core.persona import gems_persona, get_persona_list

    # B. Engineering Modules
    from modules.struktur.validator_sni import cek_dimensi_kolom, cek_rasio_tulangan, validasi_gempa_sni
    from modules.struktur import libs_sni, libs_baja, libs_bridge, libs_gempa
    
    # [SAFE IMPORT] Modul Beton & FEM (Agar tidak crash jika dependency kurang)
    try:
        from modules.struktur import libs_beton 
        from modules.struktur import libs_fem 
    except ImportError:
        pass
    
    from modules.water import libs_hidrologi, libs_irigasi, libs_jiat, libs_bendung
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research
    from modules.arch import libs_arch, libs_zoning, libs_green
    
    # C. Utility Modules (TERMASUK YANG BARU)
    from modules.utils import libs_pdf, libs_export, libs_bim_importer
    from modules.utils import libs_loader      # <--- [BARU] Universal File Reader (DXF/GIS)
    from modules.utils import libs_auto_chain  # <--- [BARU] Generator Laporan Panjang
    
    # Optional Modules (Geoteknik)
    try: 
        from modules.geotek import libs_geoteknik, libs_pondasi
        has_geotek = True
    except ImportError: 
        has_geotek = False

except ImportError as e:
    st.error(f"⚠️ **CRITICAL SYSTEM ERROR**")
    st.write(f"Gagal memuat modul engineering dasar. Pesan Error: `{e}`")
    st.stop()

# ==========================================
# REGISTRASI MODUL KE SYSTEM
# ==========================================
# Mendaftarkan modul agar bisa dipanggil oleh fungsi eksekusi dinamis
sys.modules['libs_sni'] = libs_sni
sys.modules['libs_baja'] = libs_baja
sys.modules['libs_bridge'] = libs_bridge
sys.modules['libs_gempa'] = libs_gempa

if 'libs_fem' in locals(): sys.modules['libs_fem'] = libs_fem
if 'libs_beton' in locals(): sys.modules['libs_beton'] = libs_beton

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
sys.modules['libs_loader'] = libs_loader         # Register Loader Baru
sys.modules['libs_auto_chain'] = libs_auto_chain # Register Chain Baru

if has_geotek:
    sys.modules['libs_geoteknik'] = libs_geoteknik
    sys.modules['libs_pondasi'] = libs_pondasi

# ==========================================
# 2. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(
    page_title="ENGINEX Ultimate (Gov.Ready)", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] {background-color: #F8FAFC; border-right: 1px solid #E2E8F0;}
    .stChatInput textarea {font-size: 16px !important;}
    .stDownloadButton button {width: 100%; border-radius: 6px; font-weight: 600;}
    .main-header {font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 5px;}
    .sub-header {font-size: 14px; color: #64748B; margin-bottom: 20px;}
    .audit-badge {background-color: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;}
    .streamlit-expanderHeader {
        font-size: 14px; color: #64748B; background-color: #F1F5F9; border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. HELPER FUNCTIONS & NEW FEATURES
# ==========================================

def init_project_cde(project_name):
    """
    Membuat struktur folder proyek sesuai standar ISO 19650 (AUDIT REQUIREMENT)
    """
    # Bersihkan nama folder dari karakter aneh
    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', project_name.replace(' ', '_'))
    folders = [
        "01-WIP",       # Work In Progress
        "02-SHARED",    # Koordinasi
        "03-PUBLISHED", # Siap Submit SIMBG
        "04-ARCHIVED"   # Arsip
    ]
    
    # Di Streamlit Cloud kita tidak bisa akses file system sebebas di lokal, 
    # tapi kita simpan struktur ini di Session State sebagai simulasi CDE
    if 'cde_structure' not in st.session_state:
        st.session_state.cde_structure = {}
    
    st.session_state.cde_structure[project_name] = folders
    
    # Return logs untuk ditampilkan
    return [f"✅ CDE Environment Created for {project_name}", f"📂 Folders: {', '.join(folders)}"]

def pre_audit_check_sni(data_input):
    """
    Melakukan validasi awal SNI sebelum hitungan berat (AUDIT REQUIREMENT)
    """
    errors = []
    warnings = []
    
    # Validasi SNI 2847 (Beton) - Dimensi
    if 'b_kolom' in data_input:
        if data_input['b_kolom'] < 150: # Contoh batasan
            errors.append("⛔ **CRITICAL (SNI 2847):** Dimensi kolom struktur tidak boleh < 150mm.")
    
    # Validasi SNI 1726 (Gempa) - Kategori
    if 'kategori_gempa' in data_input:
        if data_input['kategori_gempa'] in ['D', 'E', 'F'] and data_input.get('sistem_struktur') == 'Biasa':
             warnings.append("⚠️ **WARNING (SNI 1726):** Wilayah gempa kuat disarankan menggunakan SRPMK (Sistem Rangka Pemikul Momen Khusus).")

    return errors, warnings

def render_project_file_manager():
    """
    [FITUR BARU] Menyimpan (Save) dan Membuka (Open) konfigurasi proyek via JSON.
    """
    st.markdown("### 💾 File Project")
    
    col_file1, col_file2 = st.columns(2)
    
    # --- 1. FITUR SAVE (DOWNLOAD JSON) ---
    with col_file1:
        # Kumpulkan semua data penting dari Session State
        project_data = {
            "meta": {
                "app": "SmartBIM Enginex",
                "version": "Gov.Ready 2.0"
            },
            # Filter hanya data user, bukan objek backend
            "data": {k: v for k, v in st.session_state.items() 
                     if k not in ['backend', 'processed_files', 'shared_execution_vars', 'cde_structure']}
        }
        
        json_str = json.dumps(project_data, indent=4)
        
        st.download_button(
            label="📥 Save JSON",
            data=json_str,
            file_name="project_data.json",
            mime="application/json",
            use_container_width=True
        )

    # --- 2. FITUR OPEN (UPLOAD JSON) ---
    with col_file2:
        uploaded_json = st.file_uploader("Upload JSON", type=["json"], label_visibility="collapsed")
        
        if uploaded_json is not None:
            try:
                loaded_data = json.load(uploaded_json)
                
                # Update Session State
                if "data" in loaded_data:
                    for key, value in loaded_data["data"].items():
                        st.session_state[key] = value
                    
                    st.success("Data Loaded!")
                    time.sleep(0.5) # Beri waktu user melihat pesan sukses
                    st.rerun() # Refresh halaman agar input terisi
                else:
                    st.error("Format JSON tidak valid.")
            except Exception as e:
                st.error(f"Error loading: {e}")

# ==========================================
# 4. ENGINE EKSEKUSI KODE (SAFE MODE)
# ==========================================
if 'shared_execution_vars' not in st.session_state:
    st.session_state.shared_execution_vars = {}

def execute_generated_code(code_str, file_ifc_path=None):
    try:
        local_vars = st.session_state.shared_execution_vars.copy()
        
        # Helper function untuk parsing rupiah
        def parse_rupiah(txt):
            if isinstance(txt, (int, float)): return txt
            if isinstance(txt, str):
                clean = txt.replace("Rp", "").replace(" ", "").replace(".", "").replace(",", ".")
                try: return float(clean)
                except: return 0
            return 0

        # Inject library & helper (Memastikan kode AI bisa akses semua modul)
        library_kits = {
            "pd": pd, "np": np, "plt": plt, "st": st, "px": px, "go": go,
            "parse_rupiah": parse_rupiah,
            "libs_sni": libs_sni, "libs_baja": libs_baja, "libs_bridge": libs_bridge,
            "libs_gempa": libs_gempa, "libs_hidrologi": libs_hidrologi,
            "libs_irigasi": libs_irigasi, "libs_bendung": libs_bendung, "libs_jiat": libs_jiat,
            "libs_ahsp": libs_ahsp, "libs_rab_engine": libs_rab_engine,
            "libs_optimizer": libs_optimizer, "libs_research": libs_research,
            "libs_arch": libs_arch, "libs_zoning": libs_zoning, "libs_green": libs_green,
            "libs_pdf": libs_pdf, "libs_export": libs_export,
            "libs_bim_importer": libs_bim_importer,
            "libs_loader": libs_loader
        }
        
        if 'libs_fem' in globals(): library_kits['libs_fem'] = libs_fem
        if 'libs_beton' in globals(): library_kits['libs_beton'] = libs_beton
        if has_geotek:
            library_kits['libs_geoteknik'] = libs_geoteknik
            library_kits['libs_pondasi'] = libs_pondasi
            
        local_vars.update(library_kits)
        
        if file_ifc_path: 
            local_vars["file_ifc_user"] = file_ifc_path
        
        exec(code_str, local_vars)
        
        for k, v in local_vars.items():
            if k not in library_kits and not k.startswith('__') and not isinstance(v, types.ModuleType):
                st.session_state.shared_execution_vars[k] = v
        return True

    except Exception as e:
        with st.expander("⚠️ Detail Teknis (Ada kendala pada script ini)", expanded=False):
            st.warning(f"Sistem mendeteksi ketidaksesuaian: {e}")
        return False

# ==========================================
# 5. FUNGSI EXPORT (PDF SIMBG READY)
# ==========================================
# Fungsi lokal ini dipertahankan untuk backward compatibility,
# tapi disarankan menggunakan libs_pdf.create_pdf untuk hasil lebih bagus.
def clean_text_for_report(text):
    clean = re.sub(r"```python.*?```", "", text, flags=re.DOTALL)
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    return clean.strip()

def create_pdf(text_content):
    # Menggunakan fpdf untuk dokumen dasar (SIMBG Requirement: Clean PDF)
    # Ini versi simple. Untuk versi lengkap Header/Footer, gunakan libs_pdf
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 10)
            self.cell(0, 10, 'DOKUMEN TEKNIS - SMARTBIM ENGINEX (ISO 19650 COMPLIANT)', 0, 1, 'C')
    
    clean_content = clean_text_for_report(text_content)
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    # Support basic latin
    try:
        clean_content = clean_content.encode('latin-1', 'replace').decode('latin-1')
    except:
        pass
    pdf.multi_cell(0, 6, clean_content)
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 6. SIDEBAR & SETUP (UPGRADED)
# ==========================================
if 'backend' not in st.session_state: 
    st.session_state.backend = EnginexBackend()
if 'processed_files' not in st.session_state: 
    st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state: 
    st.session_state.current_expert_active = "👑 The GEMS Grandmaster"

db = st.session_state.backend

with st.sidebar:
    st.markdown("### 🛡️ ENGINEX GOV.VER")
    st.caption("Edisi Kepatuhan Audit Fase 2")
    
    # 1. KEAMANAN API KEY (AUTO-DETECT)
    api_key = get_api_key()
    if api_key:
        st.success("🔒 API Key Terdeteksi (Secure Mode)")
        genai.configure(api_key=api_key, transport="rest")
        is_secure = True
    else:
        st.warning("⚠️ Mode Publik (Tidak Aman)")
        api_key_input = st.text_input("🔑 Masukkan API Key Manual:", type="password")
        if api_key_input:
            genai.configure(api_key=api_key_input, transport="rest")
            is_secure = True
        else:
            is_secure = False
            st.error("API Key Diperlukan!")
            st.stop()

    st.divider()
    
    # 2. [BARU] FILE PROJECT MANAGER (Save/Load)
    render_project_file_manager()

    st.divider()

    # 3. NAVIGASI MENU
    selected_menu = st.radio(
        "Pilih Modul:", 
        ["🤖 AI Assistant", "🌪️ Analisis Gempa (FEM)", "🏗️ Audit Struktur"],
        label_visibility="collapsed"
    )
    
    st.divider()

    if selected_menu == "🤖 AI Assistant":
        # 4. MANAJEMEN PROYEK (CDE STANDARD)
        st.markdown("### 📂 Proyek (ISO 19650)")
        
        projects = db.daftar_proyek()
        mode = st.radio("Mode:", ["Buka Proyek", "Buat Baru"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Buat Baru":
            new_proj_name = st.text_input("Nama Proyek:", "GEDUNG-PEMDA-2025")
            if st.button("Buat & Inisiasi CDE"):
                logs = init_project_cde(new_proj_name)
                nama_proyek = new_proj_name
                st.success("Proyek & Folder CDE Terbentuk!")
                with st.expander("Lihat Log Sistem"):
                    for l in logs: st.write(l)
            else:
                nama_proyek = new_proj_name
        else:
            nama_proyek = st.selectbox("Pilih Proyek:", projects) if projects else "Default Project"
            
        # 5. PERSONA
        st.markdown("### 🎭 Persona")
        use_auto_pilot = st.checkbox("🤖 Auto-Pilot", value=True)
        if not use_auto_pilot:
            st.session_state.current_expert_active = st.selectbox("Pilih Ahli:", get_persona_list())
            
        # 6. UPLOAD (Updated for Universal Loader)
        st.markdown("### 📎 Upload Data")
        uploaded_files = st.file_uploader(
            "Upload File (CAD, GIS, PDF, Excel)",
            # Menambahkan support ekstensi baru (dxf, dwg, shp via zip, kml, dll)
            type=["png","jpg","jpeg","pdf","xlsx","docx","ifc","py", 
                  "dxf", "dwg", "geojson", "kml", "kmz", "gpx", "zip"], 
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        if st.button("🧹 Reset Chat"):
            db.clear_chat(nama_proyek, st.session_state.current_expert_active)
            st.rerun()

# ==========================================
# 7. LOGIKA TAMPILAN UTAMA
# ==========================================

# A. MODE AI ASSISTANT
if selected_menu == "🤖 AI Assistant":
    st.markdown(f'<div class="main-header">{nama_proyek} <span class="audit-badge">WIP</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Ahli Aktif: <b>{st.session_state.current_expert_active}</b></div>', unsafe_allow_html=True)

    # History
    history = db.get_chat_history(nama_proyek, st.session_state.current_expert_active)
    download_btn_counter = 0

    for msg in history:
        with st.chat_message(msg['role']):
            content = msg['content']
            parts = re.split(r"(```python.*?```)", content, flags=re.DOTALL)
            for part in parts:
                if part.startswith("```python"):
                    download_btn_counter += 1
                    code_content = part.replace("```python", "").replace("```", "").strip()
                    with st.expander("🛠️ Detail Teknis"):
                        st.code(code_content, language='python')
                    execute_generated_code(code_content)
                else:
                    st.markdown(part)

    # Input User
    prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")

    if prompt:
        target_expert = st.session_state.current_expert_active
        if use_auto_pilot: target_expert = st.session_state.current_expert_active 

        db.simpan_chat(nama_proyek, target_expert, "user", prompt)
        with st.chat_message("user"): st.markdown(prompt)

        full_prompt = [prompt]

        # LOGIKA BARU: UNIVERSAL FILE PROCESSOR
        if uploaded_files:
            for f in uploaded_files:
                if f.name not in st.session_state.processed_files:
                    
                    # 1. HANDLING GAMBAR BIASA
                    if f.name.lower().endswith(('.png','.jpg','.jpeg')): 
                        full_prompt.append(Image.open(f))
                        
                    # 2. HANDLING DOKUMEN TEXT (PDF DIBUAT HIGH-RES)
                    elif f.name.lower().endswith('.pdf'):
                        import fitz  # PyMuPDF
                        with st.spinner("🔍 Menajamkan resolusi gambar PDF untuk AI..."):
                            pdf_doc = fitz.open(stream=f.getvalue(), filetype="pdf")
                            txt = ""
                            for page_num in range(len(pdf_doc)):
                                page = pdf_doc.load_page(page_num)
                                txt += page.get_text()
                                # Render resolusi tinggi
                                mat = fitz.Matrix(3, 3) 
                                pix = page.get_pixmap(matrix=mat)
                                img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                full_prompt.append(img_data) 
                            full_prompt[0] += f"\n\n[FILE PDF: {f.name}]\n{txt}"
                        
                    # 3. HANDLING SPECIAL FILES (CAD/GIS)
                    elif f.name.lower().endswith(('.dxf', '.dwg', '.geojson', '.kml', '.kmz', '.gpx', '.zip')):
                        with st.spinner(f"Menganalisis struktur file {f.name}..."):
                            try:
                                text_data, img_data, _ = libs_loader.process_special_file(f)
                                # Pastikan variabel text_data terdefinisi sebelum dimasukkan ke f-string
                                full_prompt[0] += f"\n\n[DATA FILE: {f.name}]\n{text_data}"
                                if img_data:
                                    full_prompt.append(Image.open(img_data))
                                    with st.chat_message("user"):
                                        st.image(img_data, caption=f"Visualisasi Data: {f.name}", use_container_width=True)
                            except Exception as e:
                                st.error(f"Gagal memproses file {f.name}: {e}")

                    # 4. HANDLING FILE BIM (IFC)
                    elif f.name.lower().endswith('.ifc'):
                        with st.spinner(f"🏗️ Membedah hierarki dan elemen dari {f.name}..."):
                            import tempfile
                            try:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                                    tmp.write(f.getvalue())
                                    tmp_path = tmp.name
                                
                                engine_ifc = libs_bim_importer.BIM_Engine(tmp_path)
                                if engine_ifc.valid:
                                    elements = engine_ifc.model.by_type("IfcProduct")
                                    ifc_summary = f"Total Elemen Fisik: {len(elements)}\nSampel Elemen:\n"
                                    
                                    for el in elements[:100]:
                                        vol = engine_ifc.get_element_quantity(el)
                                        vol_text = f", Volume: {vol:.3f} m3" if vol > 0 else ""
                                        ifc_summary += f"- [{el.is_a()}] ID: {el.GlobalId}, Nama: {el.Name}{vol_text}\n"
                                        
                                    if len(elements) > 100:
                                        ifc_summary += f"\n... dan {len(elements) - 100} elemen lainnya disembunyikan untuk menghemat memori."
                                        
                                    full_prompt[0] += f"\n\n[FILE MODEL BIM IFC: {f.name}]\n{ifc_summary}"
                                    
                                    with st.chat_message("user"):
                                        st.success(f"✅ Data IFC berhasil diekstrak! ({len(elements)} elemen)")
                                else:
                                    st.error("File IFC tidak valid atau rusak.")
                            except Exception as e:
                                st.error(f"Gagal memproses IFC: {e}")
                                
                    # Tandai file sudah diproses agar tidak diulang-ulang
                    st.session_state.processed_files.add(f.name)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    persona_instr = gems_persona.get(target_expert, gems_persona["👑 The GEMS Grandmaster"])
                    # [AUDIT FIX] System Prompt Diperketat untuk Output SIMBG
                    SYS = persona_instr + """
                    \n[INSTRUKSI WAJIB UNTUK PROYEK PEMERINTAH]:
                    1. Gunakan Bahasa Indonesia Baku dan Formal (EYD).
                    2. Kode Python WAJIB menggunakan 'parse_rupiah()' untuk input harga string.
                    3. Format Laporan mengikuti standar Dokumen Lelang (Bab I, II, III...).
                    4. Tampilkan Tabel menggunakan st.table() atau st.dataframe().
                    """
                    model = genai.GenerativeModel("gemini-flash-latest",system_instruction=SYS)
                    chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                    
                    chat = model.start_chat(history=chat_hist)
                    response = chat.send_message(full_prompt)
                    
                    parts = re.split(r"(```python.*?```)", response.text, flags=re.DOTALL)
                    for part in parts:
                        if part.startswith("```python"):
                            code_content = part.replace("```python", "").replace("```", "").strip()
                            with st.expander("🛠️ Detail Teknis"):
                                st.code(code_content, language='python')
                            execute_generated_code(code_content)
                        else:
                            st.markdown(part)
                    
                    db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                    
                    # Export Button (Gov Standard)
                    st.markdown("---")
                    # Menggunakan libs_pdf yang sudah diupgrade untuk hasil lebih bagus
                    try:
                        pdf_bytes = libs_pdf.create_pdf(response.text, title="CHAT LOG REPORT")
                    except:
                        pdf_bytes = create_pdf(response.text) # Fallback ke fungsi lokal jika libs_pdf bermasalah
                        
                    if pdf_bytes: st.download_button("📄 Download Laporan (SIMBG Ready)", pdf_bytes, "Laporan_Teknis.pdf")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    
    # ==========================================
    # MODUL AUTO-CHAIN GENERATOR (INTEGRATED)
    # ==========================================
    # 1. Deteksi Kategori Modul berdasarkan Persona yang dipilih user
    active_persona = st.session_state.current_expert_active
    target_category = "STRUKTUR" # Default
    
    # Mapping Persona -> Kategori Modul
    if "Hydro" in active_persona or "Water" in active_persona:
        target_category = "WATER"
    elif "Architect" in active_persona:
        target_category = "ARSITEK"
    elif "Cost" in active_persona or "Estimator" in active_persona:
        target_category = "COST"
    elif "Geotech" in active_persona:
        target_category = "GEOTEK"
    elif "Grandmaster" in active_persona or "Struktur" in active_persona:
        target_category = "STRUKTUR"
        
    # 2. Render Panel Generator yang Sesuai
    # Ini akan memunculkan tombol generator di bawah chat
    libs_auto_chain.render_auto_chain_panel(target_category, active_persona)

# --- B. MODE FEM (ANALISIS GEMPA) ---
elif selected_menu == "🌪️ Analisis Gempa (FEM)":
    st.header("🌪️ Analisis Gempa Dinamis (FEM Engine)")
    
    # Import Module Peta Gempa
    from modules.struktur.peta_gempa_indo import get_data_kota, hitung_respon_spektrum

    # --- 1. DATA LOKASI & TANAH ---
    with st.expander("🌍 Lokasi & Data Gempa (SNI 1726:2019)", expanded=True):
        c_loc1, c_loc2 = st.columns(2)
        
        with c_loc1:
            db_kota = get_data_kota()
            # [KEY ADDED] Menambahkan key="fem_kota" agar bisa disave
            pilihan_kota = st.selectbox("📍 Pilih Lokasi Proyek", list(db_kota.keys()), index=8, key="fem_kota") 
            
            # Ambil data Ss dan S1
            data_gempa = db_kota[pilihan_kota]
            is_manual = (pilihan_kota == "Pilih Manual")
            
            # [KEY ADDED]
            Ss_input = st.number_input("Parameter Ss (0.2 detik)", value=data_gempa['Ss'], disabled=not is_manual, format="%.2f", key="fem_ss")
            S1_input = st.number_input("Parameter S1 (1.0 detik)", value=data_gempa['S1'], disabled=not is_manual, format="%.2f", key="fem_s1")

        with c_loc2:
            # [KEY ADDED]
            kelas_situs = st.selectbox("🪨 Kelas Situs Tanah", ["SA (Batuan Keras)", "SB (Batuan)", "SC (Tanah Keras)", "SD (Tanah Sedang)", "SE (Tanah Lunak)"], key="fem_kelas_tanah")
            kode_situs = kelas_situs.split()[0] # Ambil SA, SB, dst
            
            # Hitung Otomatis Parameter Desain
            hasil_gempa = hitung_respon_spektrum(Ss_input, S1_input, kode_situs)
            
            st.info(f"📊 **Parameter Desain (Otomatis):**\n\n"
                    f"**SDS = {hasil_gempa['SDS']:.3f} g** (Percepatan Desain Pendek)\n\n"
                    f"**SD1 = {hasil_gempa['SD1']:.3f} g** (Percepatan Desain 1-detik)")

    # --- 2. DATA STRUKTUR ---
    st.divider()
    st.subheader("🏗️ Geometri Struktur Portal")
    
    c1, c2 = st.columns(2)
    with c1:
        # [KEY ADDED]
        jml_lantai = st.number_input("Jumlah Lantai", 1, 50, 5, key="fem_jml_lantai")
        tinggi_lantai = st.number_input("Tinggi per Lantai (m)", 2.0, 6.0, 3.5, key="fem_tinggi_lantai")
    with c2:
        # [KEY ADDED]
        bentang_x = st.number_input("Bentang Arah X (m)", 3.0, 12.0, 6.0, key="fem_bentang_x")
        bentang_y = st.number_input("Bentang Arah Y (m)", 3.0, 12.0, 6.0, key="fem_bentang_y")
        fc_mutu = st.number_input("Mutu Beton (MPa)", 20, 60, 30, key="fem_fc")
    
    # --- 3. EKSEKUSI ---
    if st.button("🚀 Pre-Audit & Run Analysis", type="primary"):
        # Pre-Audit Sederhana
        if tinggi_lantai > 5.0 and fc_mutu < 25:
            st.error("⛔ **DITOLAK PRE-AUDIT:** Untuk tinggi tingkat > 5m, disarankan mutu beton minimal fc' 25 MPa.")
        elif 'libs_fem' not in sys.modules:
            st.error("❌ Modul FEM tidak ditemukan/gagal load.")
        else:
            with st.spinner(f"🔄 Menghitung Respon Spektrum {pilihan_kota}..."):
                try:
                    engine = libs_fem.OpenSeesEngine()
                    engine.build_simple_portal(bentang_x, bentang_y, tinggi_lantai, jml_lantai, fc_mutu)
                    df_modal = engine.run_modal_analysis(num_modes=3)
                    
                    st.success("✅ Analisis Selesai & Lolos Validasi!")
                    
                    # Tampilkan Grafik
                    st.subheader("📈 Kurva Respon Spektrum Desain")
                    T_vals = np.linspace(0, 4, 100)
                    Sa_vals = []
                    for t in T_vals:
                        if t < hasil_gempa['T0']: val = hasil_gempa['SDS'] * (0.4 + 0.6*t/hasil_gempa['T0'])
                        elif t < hasil_gempa['Ts']: val = hasil_gempa['SDS']
                        else: val = hasil_gempa['SD1'] / t
                        Sa_vals.append(val)
                        
                    fig_rsa = px.line(x=T_vals, y=Sa_vals, title=f"Respon Spektrum Desain ({pilihan_kota} - {kode_situs})")
                    fig_rsa.update_layout(xaxis_title="Periode T (detik)", yaxis_title="Percepatan Spektral Sa (g)")
                    st.plotly_chart(fig_rsa, use_container_width=True)

                    st.subheader("📊 Mode Shapes & Perioda")
                    st.dataframe(df_modal, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Terjadi Kesalahan pada Engine FEM: {e}")

# --- C. MODE AUDIT STRUKTUR ---
elif selected_menu == "🏗️ Audit Struktur":
    st.header("🏗️ Audit Forensik Struktur")
    
    if 'libs_beton' not in sys.modules:
        st.warning("⚠️ Modul `libs_beton` belum dimuat.")
    else:
        from modules.struktur.libs_beton import SNIBeton2019
        from modules.struktur.validator_sni import cek_dimensi_kolom, cek_rasio_tulangan 

        # 1. INPUT PARAMETER
        with st.expander("⚙️ Parameter Struktur & Beban", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Material**")
                # [KEY ADDED]
                fc_input = st.number_input("Mutu Beton (fc') [MPa]", value=25.0, step=5.0, key="audit_fc")
                fy_input = st.number_input("Mutu Baja (fy) [MPa]", value=420.0, step=10.0, key="audit_fy")
            with col2:
                st.markdown("**Dimensi Kolom**")
                # [KEY ADDED]
                b_input = st.number_input("Lebar (b) [mm]", value=400.0, step=50.0, key="audit_b")
                h_input = st.number_input("Tinggi (h) [mm]", value=400.0, step=50.0, key="audit_h")
            with col3:
                st.markdown("**Tulangan**")
                # [KEY ADDED]
                D_tul = st.number_input("Diameter Tulangan (D) [mm]", value=16.0, step=1.0, key="audit_D")
                n_tul = st.number_input("Jumlah Batang Total", value=8, step=2, key="audit_n")

            st.markdown("---")
            c_load1, c_load2 = st.columns(2)
            # [KEY ADDED]
            Pu_user = c_load1.number_input("Beban Aksial (Pu) [kN]", value=800.0, key="audit_Pu")
            Mu_user = c_load2.number_input("Momen Lentur (Mu) [kNm]", value=150.0, key="audit_Mu")

        # Hitung Luas Tulangan (Ast)
        Ast_input = n_tul * 0.25 * 3.14159 * (D_tul ** 2)

        # 2. LOGIKA VALIDASI & EKSEKUSI
        if st.button("🚀 Cek SNI & Jalankan Analisa"):
            
            st.divider()
            st.markdown("#### 🕵️ Laporan Pre-Audit SNI")
            
            lolos_audit = True
            
            # Cek Dimensi
            err_dim = cek_dimensi_kolom(b_input, h_input, 5) 
            if err_dim:
                for e in err_dim:
                    if "GAGAL" in e: 
                        st.error(e)
                        lolos_audit = False
                    else: st.warning(e)
            else:
                st.success("✅ Dimensi Kolom: Memenuhi Syarat Geometri.")

            # Cek Tulangan
            err_tul, rho_val = cek_rasio_tulangan(b_input, h_input, n_tul, D_tul)
            if err_tul:
                for e in err_tul:
                    if "GAGAL" in e: 
                        st.error(e)
                        lolos_audit = False
                    else: st.warning(e)
            else:
                st.success(f"✅ Tulangan: Ideal (Rasio {rho_val:.2f}%).")

            # KEPUTUSAN FINAL
            if not lolos_audit:
                st.error("🚫 **STATUS: DITOLAK.** Harap perbaiki dimensi atau tulangan sebelum menghitung.")
            
            else:
                st.info("🎉 **STATUS: LOLOS PRE-AUDIT.** Melanjutkan ke analisis kapasitas...")
                try:
                    hasil = SNIBeton2019.analyze_column_capacity(b_input, h_input, fc_input, fy_input, Ast_input, Pu_user, Mu_user)
                    pm_data = SNIBeton2019.generate_interaction_diagram(b_input, h_input, fc_input, fy_input, Ast_input)
                    
                    # VISUALISASI
                    st.divider()
                    st.subheader("📊 Hasil Analisa Akhir")
                    
                    m1, m2, m3 = st.columns(3)
                    status_aman = hasil.get('Status','-')
                    m1.metric("Status Keamanan", status_aman, delta="OK" if "AMAN" in status_aman else "-BAHAYA", delta_color="normal" if "AMAN" in status_aman else "inverse")
                    m2.metric("Rasio DCR", f"{hasil.get('DCR_Ratio',0)} x")
                    m3.metric("Kapasitas Max", f"{hasil.get('Kapasitas_Max (kN)', 0)} kN")
                    
                    df_plot = pm_data['Plot_Data']
                    fig = go.Figure()
                    
                    # Area Kapasitas
                    fig.add_trace(go.Scatter(
                        x=df_plot['M_Capacity'], y=df_plot['P_Capacity'], 
                        fill='toself', fillcolor='rgba(46, 204, 113, 0.2)', 
                        line=dict(color='#2ecc71'), name='Zona Aman'
                    ))
                    
                    # Titik Beban
                    fig.add_trace(go.Scatter(
                        x=[Mu_user], y=[Pu_user], 
                        mode='markers+text', 
                        marker=dict(size=12, color='red', symbol='x'), 
                        name='Beban Terjadi',
                        text=["Beban"], textposition="top right"
                    ))
                    
                    fig.update_layout(title="Diagram Interaksi P-M (SNI 2847:2019)", xaxis_title="Momen (kNm)", yaxis_title="Gaya Aksial (kN)", height=500)
                    st.plotly_chart(fig, use_container_width=True)

                except Exception as e:
                    st.error(f"Gagal hitung: {e}")










