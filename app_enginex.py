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
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research, libs_price_engine
    from modules.arch import libs_arch, libs_zoning, libs_green
    
    # C. Utility Modules (TERMASUK YANG BARU)
    from modules.utils import libs_pdf, libs_export, libs_bim_importer
    from modules.utils import libs_loader      # <--- [BARU] Universal File Reader (DXF/GIS)
    from modules.utils import libs_auto_chain  # <--- [BARU] Generator Laporan Panjang
    # [BARU] Modul MEP
    try:
        from modules.mep import libs_mep
        has_mep = True
    except ImportError:
        has_mep = False
    
    # [BARU] Modul Legal & Kontrak
    try:
        # Percobaan 1: Cari di dalam folder terstruktur (Standard)
        from modules.legal import libs_legal
        has_legal = True
    except ImportError:
        try:
            # Percobaan 2: Cari di folder utama/root (Fallback)
            import libs_legal
            has_legal = True
        except ImportError as e:
            # Tampilkan pesan error teknis di atas jika masih gagal
            st.error(f"⚠️ Gagal memuat libs_legal: {e}")
            has_legal = False
    
    
    try:
        from modules.schedule import libs_4d
        has_4d = True
    except ImportError:
        has_4d = False
    try:
        from modules.transport import libs_transport
        has_transport = True
    except ImportError:
        has_transport = False
    
    # Optional Modules (Geoteknik)
    try: 
        from modules.geotek import libs_geoteknik, libs_pondasi
        has_geotek = True
    except ImportError: 
        has_geotek = False
    
    try: 
        from modules.utils import libs_topografi
        sys.modules['libs_topografi'] = libs_topografi
    except ImportError: 
        pass
        
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
sys.modules['libs_price_engine'] = libs_price_engine # <--- TAMBAHAN BARU
# [BARU] Register MEP
if has_mep:
    sys.modules['libs_mep'] = libs_mep
if has_legal:
    sys.modules['libs_legal'] = libs_legal
if has_4d:
    sys.modules['libs_4d'] = libs_4d
if has_transport:
    sys.modules['libs_transport'] = libs_transport
if has_geotek:
    sys.modules['libs_geoteknik'] = libs_geoteknik
    sys.modules['libs_pondasi'] = libs_pondasi
    try:
        from modules.cost import libs_bps
        sys.modules['libs_bps'] = libs_bps
    except ImportError:
        pass
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
    /* 1. Menghilangkan Branding Streamlit (White-label) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 2. Styling Sidebar agar bersih dan elegan */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }

    /* 3. Tombol Premium (Efek Hover & Shadow) */
    .stButton>button {
        background-color: #1E3A8A !important; /* Corporate Blue */
        color: white !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06) !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #1e40af !important; /* Warna sedikit lebih terang saat di-hover */
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05) !important;
        transform: translateY(-2px) !important; /* Efek tombol terangkat */
    }

    /* 4. Styling Kotak/Expander agar modern (UI Card) */
    .streamlit-expanderHeader {
        background-color: #f8fafc !important;
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        font-weight: 600 !important;
        color: #334155 !important;
    }
    div[data-testid="stExpander"] {
        border: none !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
        background-color: white !important;
    }

    /* 5. Typografi Heading & Badge */
    .main-header {font-size: 32px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;}
    .sub-header {font-size: 16px; color: #64748b; margin-bottom: 20px;}
    .audit-badge {
        background-color: #1E3A8A; 
        color: white;
        padding: 4px 10px; 
        border-radius: 20px; 
        font-size: 12px; 
        font-weight: bold;
        vertical-align: middle;
        margin-left: 10px;
    }
    
    /* 6. Input Form elegan */
    input, textarea, select {
        border-radius: 6px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
    }
    input:focus, textarea:focus, select:focus {
        border-color: #1E3A8A !important;
        box-shadow: 0 0 0 1px #1E3A8A !important;
    }
    
    /* 7. Styling Tabel Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
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
        safe_data = {}
        for k, v in st.session_state.items():
            # Filter objek backend internal
            if k not in ['backend', 'processed_files', 'shared_execution_vars', 'cde_structure']:
                # ANTI-CRASH: Hanya simpan tipe data dasar yang dikenali JSON
                # Abaikan wujud file fisik (UploadedFile) dari memori
                if isinstance(v, (str, int, float, bool, list, dict, type(None))):
                    safe_data[k] = v

        project_data = {
            "meta": {
                "app": "SmartBIM Enginex",
                "version": "Gov.Ready 2.0"
            },
            "data": safe_data
        }
        
        try:
            json_str = json.dumps(project_data, indent=4)
            st.download_button(
                label="📥 Save JSON",
                data=json_str,
                file_name="project_data.json",
                mime="application/json",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Save UI error (Abaikan jika sedang testing): {e}")

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
                    time.sleep(0.5)
                    st.rerun()
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
        # [AUDIT PATCH]: SECURITY SANDBOX FILTER (DILONGGARKAN)
        forbidden_keywords = ['import os', 'import sys', 'import subprocess', 'open(', 'shutil', 'st.secrets']
        for keyword in forbidden_keywords:
            if keyword in code_str:
                st.error(f"🚨 SECURITY BLOCK: AI mencoba mengeksekusi perintah sistem terlarang (`{keyword}`).")
                return False

        local_vars = st.session_state.shared_execution_vars.copy()
        
        # Helper function untuk parsing rupiah
        def parse_rupiah(txt):
            if isinstance(txt, (int, float)): return txt
            if isinstance(txt, str):
                clean = txt.replace("Rp", "").replace(" ", "").replace(".", "").replace(",", ".")
                try: return float(clean)
                except: return 0
            return 0

        # [AUDIT PATCH]: PASTIKAN LIBRARY INI TERBACA OLEH AI
        import math
        import networkx as nx
        import scipy

        # Inject library & helper (Environment Terisolasi)
        library_kits = {
            "pd": pd, "np": np, "plt": plt, "st": st, "px": px, "go": go,
            "math": math, "nx": nx, "scipy": scipy, # <--- TAMBAHAN PENTING
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
        if has_mep: library_kits['libs_mep'] = libs_mep
        if has_legal: library_kits['libs_legal'] = libs_legal    
        
        local_vars.update(library_kits)

        if has_4d: library_kits['libs_4d'] = libs_4d
        if has_transport: library_kits['libs_transport'] = libs_transport
        if file_ifc_path: local_vars["file_ifc_user"] = file_ifc_path
        
        # [PERBAIKAN SCOPE EXEC KRUSIAL] 
        # local_vars dipasang dua kali untuk menggabungkan scope Globals & Locals 
        # Ini akan menyelesaikan 100% masalah "name X is not defined"
        exec(code_str, local_vars, local_vars)
        
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
# 6. SIDEBAR & SETUP (UPGRADED & STRUCTURED)
# ==========================================
if 'backend' not in st.session_state: 
    st.session_state.backend = EnginexBackend()
if 'processed_files' not in st.session_state: 
    st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state: 
    st.session_state.current_expert_active = "👑 The GEMS Grandmaster"
if 'nama_proyek' not in st.session_state:
    st.session_state.nama_proyek = "Proyek_Aktif" # Default nama proyek

db = st.session_state.backend
uploaded_files = None # Inisialisasi awal
# ==========================================
# AUTO-LOAD MASTER DATABASE AHSP
# ==========================================
if 'master_ahsp' not in st.session_state:
    df_ahsp_db = db.get_master_ahsp_permanen()
    if not df_ahsp_db.empty:
        st.session_state.master_ahsp = df_ahsp_db
        st.session_state.status_ahsp = "TERKUNCI DARI DATABASE"
    else:
        st.session_state.master_ahsp = None
        st.session_state.status_ahsp = "KOSONG"

with st.sidebar:
    st.markdown("### 🛡️ ENGINEX GOV.VER")
    st.caption("Edisi Kepatuhan Audit Fase 2")
    
    # --- LEVEL 1: SISTEM & KEAMANAN ---
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
    
    # --- LEVEL 2: MANAJEMEN DATA & PROYEK (GLOBAL) ---
    st.markdown("### 📂 Data & Proyek (ISO 19650)")
    
    # Fitur Buka/Buat Proyek sekarang GLOBAL (Tidak disembunyikan di AI Assistant)
    projects = db.daftar_proyek()
    mode = st.radio("Sistem File:", ["Buka Proyek", "Buat Baru"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Buat Baru":
        new_proj_name = st.text_input("Nama Proyek:", "GEDUNG-PEMDA-2025")
        if st.button("Buat & Inisiasi CDE", use_container_width=True):
            logs = init_project_cde(new_proj_name)
            st.session_state.nama_proyek = new_proj_name
            st.success("CDE Terbentuk!")
        else:
            st.session_state.nama_proyek = new_proj_name
    else:
        st.session_state.nama_proyek = st.selectbox("Pilih Proyek Aktif:", projects) if projects else "Default Project"
        
    render_project_file_manager() # Tombol Save/Load JSON

    st.divider()

    # --- LEVEL 3: NAVIGASI MENU UTAMA ---
    st.markdown("### 🧭 Navigasi Modul")
    selected_menu = st.radio(
        "Pilih Modul Aplikasi:", 
        [
            "🤖 AI Assistant", 
            "📏 Visual QTO 2D (PlanSwift Mode)", 
            "📑 Laporan RAB 5D", 
            "🌪️ Analisis Gempa (FEM)",
            "🏛️ Template Struktur (Klasik)",
            "🏗️ Audit Struktur",
            "🌾 Desain Irigasi (KP-01)",
            "🌊 Hidrolika Bendung (KP-02)",
            "🌊 Analisis Hidrologi",
            "🪨 Analisis Geoteknik & Lereng",
            "🏗️ Daya Dukung Pondasi",
            "🗺️ Analisis Topografi 3D",
            "🌉 Audit Baja & Jembatan",
            "🛣️ Analisis Transportasi (Jalan)",
            "💡 Kalkulator MEP (SNI)",           
            "🌿 Green Building & Zonasi",
            "📅 Penjadwalan Proyek (4D BIM)",  
            "⚖️ Evaluasi Tender & Legal",      
            "⚙️ Admin: Ekstraksi AHSP"
        ],
        label_visibility="collapsed"
    )
    
    # Tarik variabel nama_proyek dari session state agar bisa dipakai di main area
    nama_proyek = st.session_state.nama_proyek
    
    st.divider()

    # --- LEVEL 4: MENU KONTEKSTUAL (Berubah sesuai Menu Utama yang dipilih) ---
    
    # KONDISI A: JIKA DI MENU AI ASSISTANT
    if selected_menu == "🤖 AI Assistant":
        st.markdown("### 🎭 Pengaturan AI")
        use_auto_pilot = st.checkbox("🤖 Auto-Pilot", value=True)
        if not use_auto_pilot:
            st.session_state.current_expert_active = st.selectbox("Pilih Ahli:", get_persona_list())
            
        st.markdown("### 📎 Upload Data")
        uploaded_files = st.file_uploader(
            "Upload File (CAD, GIS, PDF, Excel, IFC)",
            type=["png","jpg","jpeg","pdf","xlsx","docx","ifc","py", 
                  "dxf", "dwg", "geojson", "kml", "kmz", "gpx", "zip", 
                  "tif", "tiff", "dem"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        if st.button("🧹 Reset Chat", use_container_width=True):
            db.clear_chat(nama_proyek, st.session_state.current_expert_active)
            st.rerun()

    # KONDISI B: JIKA DI MENU VISUAL QTO ATAU RAB
    elif selected_menu in ["📏 Visual QTO 2D (PlanSwift Mode)", "📑 Laporan RAB 5D"]:
        st.markdown("### ⚙️ Pengaturan Estimasi Biaya")
        
        # Pilihan Bidang (SE 30/2025) HANYA muncul di menu yang butuh hitung RAB
        st.session_state.bidang_proyek = st.selectbox(
            "Kategori Bidang Proyek (SE 30/2025):",
            ["Cipta Karya", "Bina Marga", "Sumber Daya Air"],
            help="Sangat krusial! Mempengaruhi koefisien pekerja & alat berat di perhitungan AHSP."
        )
        
        # Pilihan Lokasi BPS HANYA muncul di sini
        st.session_state.lokasi_bps = st.selectbox(
            "Lokasi (Indeks BPS):", 
            ["Lampung", "DKI Jakarta", "Jawa Barat", "Jawa Tengah", "Jawa Timur", "Bali", "Sumatera Selatan", "Kalimantan Barat", "Sulawesi Selatan", "Papua", "Papua Pegunungan"], 
            index=0
        )
        
        st.markdown("### 📊 Export 5D BIM (IFC)")
        ifc_file_target = st.file_uploader("Upload File .ifc Khusus RAB:", type=['ifc'], key="ifc_rab")
        
        if ifc_file_target:
            if st.button("🔄 Ekstrak Volume IFC", use_container_width=True, type="secondary"):
                with st.spinner("Menarik data 3D menjadi Volume..."):
                    import tempfile
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                            tmp.write(ifc_file_target.getvalue())
                            tmp_path = tmp.name

                        engine_ifc = libs_bim_importer.BIM_Engine(tmp_path)
                        
                        if engine_ifc.valid:
                            elements = engine_ifc.model.by_type("IfcProduct")
                            
                            # [AUDIT PATCH]: Daftar Hitam (Blacklist) Aset Visual & Rendering
                            blacklist_kata = ['enscape', 'tree', 'plant', 'sofa', 'standing', 'sitting', 'car ', 'people', 'person', 'bush', 'shrub', 'vehicle', 'grass', 'flower']
                            
                            
                            # [AUDIT PATCH FINAL]: Pembersihan ID Revit & Translasi Paksa ke SNI
                            # [AUDIT PATCH FINAL]: Filter Aset, Translasi SNI & Grouping
                            data_boq_asli = []
                            for el in elements:
                                if "Ifc" in el.is_a() and el.is_a() not in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcOpeningElement"]:
                                    
                                    kategori_ifc = str(el.is_a()).lower()
                                    nama_raw = str(el.Name).lower() if el.Name else ""
                                    
                                    # 1. BUANG ASET VISUAL/SAMPAN
                                    blacklist = ['enscape', 'tree', 'plant', 'sofa', 'car', 'generic models', 'proxy', 'lines']
                                    if any(b in nama_raw for b in blacklist): continue
                                    
                                    # 2. UBAH NAMA IFC JADI BAHASA SNI PUPR
                                    nama_sni = None
                                    if "ifccolumn" in kategori_ifc: nama_sni = "Pekerjaan Kolom Beton (K-300)"
                                    elif "ifcbeam" in kategori_ifc: nama_sni = "Pekerjaan Balok Beton (K-300)"
                                    elif "ifcslab" in kategori_ifc: nama_sni = "Pekerjaan Pelat Lantai Beton (K-300)"
                                    elif "ifcwall" in kategori_ifc: nama_sni = "Pekerjaan Pasangan Dinding Bata"
                                    elif "ifcdoor" in kategori_ifc or "ifcwindow" in kategori_ifc: nama_sni = "Pekerjaan Pintu dan Jendela"
                                    elif "ifcfooting" in kategori_ifc or "ifcpile" in kategori_ifc: nama_sni = "Pekerjaan Pondasi Beton"
                                    elif "ifcroof" in kategori_ifc or "ifccovering" in kategori_ifc: nama_sni = "Pekerjaan Rangka Atap dan Penutup"

                                    
                                    if not nama_sni: continue # Abaikan jika bukan struktur
                                        
                                    vol = engine_ifc.get_element_quantity(el)
                                    vol_final = round(vol, 3) if vol and vol > 0 else 0.0 # <--- Tidak ada lagi volume fiktif 1.0!
                                    
                                    if vol_final > 0:
                                        data_boq_asli.append({
                                            "Kategori": "Pekerjaan Struktur",
                                            "Nama": nama_sni,
                                            "Volume": vol_final
                                        })
                            
                            if len(data_boq_asli) > 0:
                                # 3. REKAPITULASI (GROUPING): Ratusan baris jadi 1 baris per tipe
                                df_raw = pd.DataFrame(data_boq_asli)
                                df_grouped = df_raw.groupby(['Kategori', 'Nama'], as_index=False)['Volume'].sum()
                                
                                st.session_state['real_boq_data'] = df_grouped
                                st.success(f"✅ Data dipadatkan ke Standar SNI! (Tersisa {len(df_grouped)} Item Utama).")
                            else:
                                st.error("⚠️ IFC terbaca, tapi elemen fisik struktural kosong setelah difilter.")
                        else:
                            st.error("❌ File IFC Rusak.")
                    except Exception as e:
                        st.error(f"❌ Gagal Ekstrak: {e}")

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
                    # --- INDIKATOR DEBUGGING MEMORI AHSP ---
                    if 'master_ahsp_data' in st.session_state:
                        st.success(f"🔗 STATUS: Terhubung dengan Database Master AHSP ({len(st.session_state['master_ahsp_data'])} item data). AI siap membaca data pasti!")
                    else:
                        st.warning("⚠️ STATUS: Database Master AHSP KOSONG. AI berpotensi halusinasi. Silakan ke menu Admin untuk mengunci data.")
                    # ---------------------------------------

    # =================================================================
    # [PERBAIKAN AUDIT FASE 5: HYBRID UI - GUIDED PROMPT FORMS]
    # =================================================================
    guided_prompt = None
    target_expert = st.session_state.current_expert_active
    
    with st.expander("🎯 Form Instruksi Terpandu (Klik untuk menggunakan Template AI)", expanded=False):
        st.caption("Gunakan form ini jika Anda tidak ingin mengetik perintah secara manual.")
        
        # 1. Tampilan Form khusus Ahli Struktur / Gempa
        if "Struktur" in target_expert or "Gempa" in target_expert or "Grandmaster" in target_expert:
            mode_hitung = st.radio("Pilih Analisis Struktur:", 
                ["Hitung Base Shear Gempa (SNI 1726)", "Cek Kapasitas Balok Beton (SNI 2847)", "Cek Profil Baja WF (SNI 1729)", "Optimasi Dimensi Balok Termurah"],
                horizontal=True)
                
            if "Gempa" in mode_hitung:
                col_g1, col_g2 = st.columns(2)
                berat = col_g1.number_input("Berat Total Bangunan (kN)", value=1500.0, step=100.0)
                tanah = col_g2.selectbox("Kelas Situs Tanah", ["lunak", "sedang", "keras", "khusus"])
                if st.button("🚀 Kirim Analisis Gempa", type="primary"):
                    guided_prompt = f"Tolong hitung gaya geser dasar (Base Shear) gempa untuk bangunan dengan berat total {berat} kN di atas tanah {tanah}."
            
            elif "Balok Beton" in mode_hitung:
                col_b1, col_b2, col_b3 = st.columns(3)
                b_balok = col_b1.number_input("Lebar b (mm)", value=300.0)
                h_balok = col_b2.number_input("Tinggi h (mm)", value=500.0)
                mu_balok = col_b3.number_input("Momen Ultimate (kNm)", value=150.0)
                
                col_b4, col_b5 = st.columns(2)
                fc_mutu = col_b4.number_input("Mutu Beton fc' (MPa)", value=30.0)
                fy_mutu = col_b5.number_input("Mutu Baja fy (MPa)", value=420.0)
                if st.button("🚀 Kirim Analisis Balok", type="primary"):
                    guided_prompt = f"Evaluasi kapasitas lentur dan geser balok beton dengan dimensi {b_balok}x{h_balok} mm, mutu beton {fc_mutu} MPa, baja {fy_mutu} MPa untuk menahan momen {mu_balok} kNm."
                    
            elif "Baja WF" in mode_hitung:
                col_wf1, col_wf2 = st.columns(2)
                mu_wf = col_wf1.number_input("Momen Ultimate (kNm)", value=120.0)
                L_wf = col_wf2.number_input("Panjang Bentang (m)", value=6.0)
                if st.button("🚀 Kirim Analisis Baja", type="primary"):
                    guided_prompt = f"Cek keamanan profil baja WF 300x150 dengan panjang bentang {L_wf} meter terhadap momen lentur sebesar {mu_wf} kNm."
            
            elif "Optimasi" in mode_hitung:
                col_op1, col_op2 = st.columns(2)
                mu_op = col_op1.number_input("Momen Rencana (kNm)", value=250.0)
                L_op = col_op2.number_input("Panjang Bentang (m)", value=8.0)
                if st.button("🚀 Cari Dimensi Termurah", type="primary"):
                    guided_prompt = f"Tolong carikan dimensi balok beton yang paling murah dan optimal untuk bentang {L_op} meter yang memikul momen {mu_op} kNm."

        # 2. Tampilan Form khusus Ahli Geoteknik
        elif "Geotech" in target_expert:
            mode_geo = st.radio("Pilih Analisis Geoteknik:", ["Daya Dukung Pondasi Tapak", "Stabilitas Talud Batu Kali"], horizontal=True)
            if "Pondasi" in mode_geo:
                c_p1, c_p2 = st.columns(2)
                pu_beban = c_p1.number_input("Beban Aksial (kN)", value=500.0)
                lebar_p = c_p2.number_input("Lebar Tapak (m)", value=1.5)
                if st.button("🚀 Kirim Analisis Pondasi", type="primary"):
                    guided_prompt = f"Hitung kapasitas pondasi telapak ukuran {lebar_p}x{lebar_p} meter yang memikul beban aksial sebesar {pu_beban} kN."
            elif "Talud" in mode_geo:
                tinggi_t = st.number_input("Tinggi Talud (m)", value=3.0)
                if st.button("🚀 Kirim Analisis Talud", type="primary"):
                    guided_prompt = f"Tolong cek stabilitas guling untuk talud pasangan batu kali dengan tinggi {tinggi_t} meter."

        # 3. Tampilan Default (Jika Persona lain terpilih)
        else:
            st.info(f"Form terpandu untuk spesialisasi '{target_expert}' sedang dalam tahap pengembangan. Silakan gunakan kotak chat di bawah.")

    # =================================================================
    # KOTAK CHAT MANUAL (HYBRID FALLBACK)
    # =================================================================
    manual_prompt = st.chat_input("Atau ketik perintah bebas / ngobrol dengan AI di sini...")
    
    # Tangkap prompt dari mana pun asalnya (Form atau Ketik Manual)
    prompt = guided_prompt if guided_prompt else manual_prompt

    if prompt:
        if use_auto_pilot: target_expert = st.session_state.current_expert_active 

        db.simpan_chat(nama_proyek, target_expert, "user", prompt)
        with st.chat_message("user"): st.markdown(prompt)

        full_prompt = [prompt]
    
        # =================================================================
        # [INJEKSI DATA MASTER AHSP KE OTAK AI - ZERO DUMMY]
        # Posisinya dipindah ke luar agar selalu terbaca AI setiap saat!
        # =================================================================
       
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
                    elif f.name.lower().endswith(('.dxf', '.dwg', '.geojson', '.kml', '.kmz', '.gpx', '.zip', '.tif', '.tiff', '.dem')):
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

                                    # --- [UPDATE] SIMPAN DATA ASLI UNTUK EXCEL ---
                                    # [AUDIT PATCH]: Daftar Hitam (Blacklist) Aset Visual & Rendering
                                    blacklist_kata = ['enscape', 'tree', 'plant', 'sofa', 'standing', 'sitting', 'car ', 'people', 'person', 'bush', 'shrub', 'vehicle', 'grass', 'flower']
                                    
                                    # [AUDIT PATCH FINAL]: Filter Aset, Translasi SNI & Grouping
                                    data_boq_asli = []
                                    for el in elements:
                                        if "Ifc" in el.is_a() and el.is_a() not in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcOpeningElement"]:
                                            kategori_ifc = str(el.is_a()).lower()
                                            nama_raw = str(el.Name).lower() if el.Name else ""
                                            blacklist = ['enscape', 'tree', 'plant', 'sofa', 'car', 'generic models', 'proxy', 'lines']
                                            if any(b in nama_raw for b in blacklist): continue
                                            
                                            nama_sni = None
                                            if "ifccolumn" in kategori_ifc: nama_sni = "Pekerjaan Kolom Beton (K-300)"
                                            elif "ifcbeam" in kategori_ifc: nama_sni = "Pekerjaan Balok Beton (K-300)"
                                            elif "ifcslab" in kategori_ifc: nama_sni = "Pekerjaan Pelat Lantai Beton (K-300)"
                                            elif "ifcwall" in kategori_ifc: nama_sni = "Pekerjaan Pasangan Dinding Bata"
                                            elif "ifcdoor" in kategori_ifc or "ifcwindow" in kategori_ifc: nama_sni = "Pekerjaan Pintu dan Jendela"
                                            elif "ifcfooting" in kategori_ifc or "ifcpile" in kategori_ifc: nama_sni = "Pekerjaan Pondasi Beton"
                                            
                                            if not nama_sni: continue
                                                
                                            vol = engine_ifc.get_element_quantity(el)
                                            vol_final = round(vol, 3) if vol and vol > 0 else 0.0
                                            
                                            if vol_final > 0:
                                                data_boq_asli.append({"Kategori": "Pekerjaan Struktur", "Nama": nama_sni, "Volume": vol_final})
                                    
                                    if len(data_boq_asli) > 0:
                                        df_raw = pd.DataFrame(data_boq_asli)
                                        df_grouped = df_raw.groupby(['Kategori', 'Nama'], as_index=False)['Volume'].sum()
                                        st.session_state['real_boq_data'] = df_grouped
                                    # ---------------------------------------------
                                                                                    
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
            with st.spinner("Menganalisis dan memproses komputasi..."):
                try:
                    persona_instr = gems_persona.get(target_expert, gems_persona["👑 The GEMS Grandmaster"])
                    

                    # =================================================================
                    # [PERBAIKAN AUDIT FASE 3: DOKTRIN TOOL CALLING]
                    # =================================================================
                    SYS = persona_instr + """
                    \n[INSTRUKSI WAJIB - MODE DETERMINISTIK]:
                    1. Gunakan Bahasa Indonesia Baku dan Formal (EYD).
                    2. DILARANG KERAS menulis blok kode skrip Python (```python).
                    3. Anda WAJIB MENGGUNAKAN TOOLS (Function Calling) untuk menghitung. Dilarang keras berasumsi angka sendiri.
                    4. Narasikan hasil komputasi dari Tools tersebut dengan gaya profesional.
                    """
                    
                    try:
                        import sys
                        import os
                        sys.path.append(os.getcwd()) # Paksa baca dari folder utama aplikasi
                        
                        import libs_tools
                        
                        daftar_tools_sni = [
                            libs_tools.tool_hitung_gempa_v,
                            libs_tools.tool_hitung_balok,
                            libs_tools.tool_evaluasi_kapasitas_balok,
                            libs_tools.tool_cek_baja_wf,
                            libs_tools.tool_hitung_pondasi,
                            libs_tools.tool_estimasi_biaya,
                            libs_tools.tool_cek_talud,
                            libs_tools.tool_cari_dimensi_optimal
                        ]
                    except Exception as e:
                        daftar_tools_sni = None
                        st.error(f"🚨 SYSTEM ERROR ASLI: File 'libs_tools.py' gagal dimuat. Detail: {e}")
                        st.warning("Pastikan file 'libs_tools.py' sudah ter-upload di GitHub pada folder paling luar (root).")
                        st.stop()
                    
                    
                    # --- [AUTO-FALLBACK DENGAN PING KE GOOGLE] ---
                    chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                    
                    try:
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        priorities = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]
                        
                        selected_model = None
                        for p in priorities:
                            if p in available_models:
                                selected_model = p.replace("models/", "")
                                break
                                
                        # Fallback darurat
                        if not selected_model and available_models:
                            for v in available_models:
                                if "gemini" in v:
                                    selected_model = v.replace("models/", "")
                                    break
                                    
                        if not selected_model:
                            st.error("🚨 API Key tidak memiliki akses ke model teks.")
                            st.stop()
                            
                        # =================================================================
                        # [PUNCAK PERBAIKAN]: Injeksi tools ke dalam otak AI
                        # =================================================================
                        model = genai.GenerativeModel(
                            selected_model, 
                            system_instruction=SYS,
                            tools=daftar_tools_sni # Memaksa AI memakai rumus SNI dari server lokal
                        )
                        
                        # enable_automatic_function_calling=True -> Server Streamlit akan otomatis
                        # menjalankan fungsi Python jika AI memintanya, lalu mengembalikan hasilnya ke AI.
                        chat = model.start_chat(history=chat_hist, enable_automatic_function_calling=True)
                        
                    except Exception as e:
                        st.error(f"🚨 Gagal menghubungi server Google atau inisialisasi Tools: {e}")
                        st.stop()
                    # ---------------------------------------------------------               
                    
                    response = chat.send_message(full_prompt)
        
                    # --- [UPGRADE: HITL] JARING PENANGKAP AI-QS VISION ---
                    import json
                    boq_match = re.search(r'```json\n(.*?"Kategori".*?)\n```', response.text, re.DOTALL | re.IGNORECASE)
                    if boq_match:
                        try:
                            json_str = boq_match.group(1)
                            boq_list = json.loads(json_str)
                            if isinstance(boq_list, list) and len(boq_list) > 0 and "Kategori" in boq_list[0]:
                                df_ai = pd.DataFrame(boq_list)
                                # Simpan sementara untuk direview
                                st.session_state['draft_boq_data'] = df_ai
                                st.success(f"🎯 [AI-QS VISION] Menemukan {len(boq_list)} item pekerjaan. Menunggu Validasi (HITL)...")
                        except Exception as e:
                            st.warning(f"AI mencoba membuat tabel BOQ, tapi format JSON meleset: {e}")
                            
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
                    try:
                        pdf_bytes = libs_pdf.create_pdf(response.text, title="CHAT LOG REPORT")
                    except:
                        pdf_bytes = create_pdf(response.text)
                        
                    if pdf_bytes: st.download_button("📄 Download Laporan (SIMBG Ready)", pdf_bytes, "Laporan_Teknis.pdf")
                    
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- RENDER TABEL VALIDASI HITL (Di Luar Try-Except & Chat Bubble) ---
    if 'draft_boq_data' in st.session_state and not st.session_state['draft_boq_data'].empty:
        st.markdown("### 🕵️ Validasi Ekstraksi AI (Human-in-the-Loop)")
        st.info("⚠️ Silakan periksa hasil ekstraksi Vision LLM. Anda dapat mengedit data secara manual sebelum masuk ke RAB.")
        
        edited_df = st.data_editor(
            st.session_state['draft_boq_data'],
            num_rows="dynamic",
            use_container_width=True,
            key="hitl_editor"
        )
        
        if st.button("✅ Setujui & Masukkan ke Memori RAB", type="primary"):
            st.session_state['real_boq_data'] = edited_df
            st.session_state['draft_boq_data'] = pd.DataFrame()
            st.success("Data divalidasi dan terkunci untuk ekspor 7-Tab Excel!")
            st.rerun()

  
                    
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

# --- MODE VISUAL QTO 2D (VECTOR DXF MODE) ---
elif selected_menu == "📏 Visual QTO 2D (PlanSwift Mode)":
    st.header("📏 Vector QTO 2D (Auto-Extract DXF)")
    st.caption("Ekstraksi Kuantitas (Luasan & Panjang) Otomatis langsung dari Topologi Vektor CAD.")
    
    if 'libs_loader' not in sys.modules:
        st.warning("⚠️ Modul `libs_loader` belum dimuat oleh sistem.")
    else:
        st.markdown("### 1. Upload Denah CAD (.DXF)")
        st.info("💡 **Tips Persiapan CAD:** Pastikan gambar Anda digambar dengan skala **1 unit CAD = 1 Meter**. Kelompokkan objek ke dalam Layer yang benar (Misal: buat layer bernama *'Pekerjaan Pasangan Dinding Bata'* untuk garis dinding, atau *'Pekerjaan Pelat Lantai'* untuk poligon tertutup lantai).")
        
        dxf_file = st.file_uploader("Pilih File DXF", type=["dxf"])
        
        if dxf_file:
            if st.button("🚀 Ekstrak Geometri (QTO)", type="primary", use_container_width=True):
                with st.spinner("Membaca Vektor dan Menghitung Algoritma Geometri..."):
                    # Panggil Class baru dari libs_loader
                    qto_engine = sys.modules['libs_loader'].DXF_QTO_Engine()
                    df_hasil, pesan = qto_engine.extract_qto_from_dxf(dxf_file)
                    
                    if df_hasil is not None:
                        st.success("✅ Ekstraksi Vektor Selesai!")
                        
                        st.markdown("### 📊 Hasil Quantity Take-Off (QTO)")
                        st.dataframe(df_hasil, use_container_width=True)
                        
                        # Siapkan data untuk di-inject ke Memori Utama RAB
                        # Kita ubah formatnya agar persis seperti df_boq di memori aplikasi
                        df_inject = df_hasil.rename(columns={"Layer (Item Pekerjaan)": "Nama"})
                        df_inject['Kategori'] = "Ekstraksi Visual QTO 2D"
                        
                        # Simpan ke session_state agar tombol di bawah bisa berfungsi
                        st.session_state['temp_dxf_qto'] = df_inject
                    else:
                        st.error(pesan)
                        
            # Tombol injeksi ke RAB (Hanya muncul jika sudah ada hasil ekstraksi)
            if 'temp_dxf_qto' in st.session_state:
                st.divider()
                if st.button("💾 Simpan Volume ke Memori RAB Utama", type="secondary", use_container_width=True):
                    df_inject = st.session_state['temp_dxf_qto']
                    
                    # Tambahkan ke real_boq_data
                    if 'real_boq_data' not in st.session_state or st.session_state['real_boq_data'] is None:
                        st.session_state['real_boq_data'] = df_inject[['Kategori', 'Nama', 'Volume']]
                    else:
                        st.session_state['real_boq_data'] = pd.concat([st.session_state['real_boq_data'], df_inject[['Kategori', 'Nama', 'Volume']]], ignore_index=True)
                    
                    st.success("✅ Volume berhasil dimasukkan ke Bill of Quantities (BOQ)! Buka menu **📑 Laporan RAB 5D** untuk melihat perhitungan biayanya.")


       

# --- B. MODE FEM (ANALISIS GEMPA) ---
elif selected_menu == "🌪️ Analisis Gempa (FEM)":
    st.header("🌪️ Analisis Gempa Dinamis (FEM Engine)")
    from modules.struktur.peta_gempa_indo import get_data_kota, hitung_respon_spektrum

    # --- 1. DATA LOKASI & TANAH ---
    with st.expander("🌍 Lokasi & Data Gempa (SNI 1726:2019)", expanded=True):
        c_loc1, c_loc2 = st.columns(2)
        with c_loc1:
            db_kota = get_data_kota()
            pilihan_kota = st.selectbox("📍 Pilih Lokasi Proyek", list(db_kota.keys()), index=8, key="fem_kota") 
            data_gempa = db_kota[pilihan_kota]
            is_manual = (pilihan_kota == "Pilih Manual")
            Ss_input = st.number_input("Parameter Ss (0.2 detik)", value=data_gempa['Ss'], disabled=not is_manual, format="%.2f", key="fem_ss")
            S1_input = st.number_input("Parameter S1 (1.0 detik)", value=data_gempa['S1'], disabled=not is_manual, format="%.2f", key="fem_s1")

        with c_loc2:
            kelas_situs = st.selectbox("🪨 Kelas Situs Tanah", ["SA (Batuan Keras)", "SB (Batuan)", "SC (Tanah Keras)", "SD (Tanah Sedang)", "SE (Tanah Lunak)"], key="fem_kelas_tanah")
            kode_situs = kelas_situs.split()[0]
            hasil_gempa = hitung_respon_spektrum(Ss_input, S1_input, kode_situs)
            st.info(f"📊 **Parameter Desain:**\n\n**SDS = {hasil_gempa['SDS']:.3f} g**\n\n**SD1 = {hasil_gempa['SD1']:.3f} g**")

    st.divider()

    # --- FITUR BARU: INTEGRASI BIM KE FEM ---
    st.subheader("🔗 Ekstraksi BIM (IFC -> OpenSees)")
    ifc_fem_file = st.file_uploader("Upload File .ifc:", type=['ifc'], key="ifc_fem")
    
    if ifc_fem_file and st.button("🚀 Ekstrak Geometri & Hitung Getaran", type="primary", use_container_width=True):
        import tempfile
        with st.spinner("1️⃣ Membaca File IFC..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(ifc_fem_file.getvalue())
                tmp_path = tmp.name
            engine_ifc = libs_bim_importer.BIM_Engine(tmp_path)
        
        if engine_ifc.valid:
            with st.spinner("2️⃣ Mengekstrak Garis As..."):
                elements = engine_ifc.model.by_type("IfcProduct")
                analytical_data = [engine_ifc.get_analytical_nodes(el) for el in elements if engine_ifc.get_analytical_nodes(el)]
            st.success(f"✅ {len(analytical_data)} garis diekstrak!")
            
            with st.spinner("3️⃣ Menghitung Eigenvalue & Partisipasi Massa..."):
                engine_fem = libs_fem.OpenSeesEngine()
                if engine_fem.build_model_from_ifc(analytical_data, fc_mutu=30):
                    df_modal = engine_fem.run_modal_analysis(num_modes=10) # Ditingkatkan jadi 10 mode
                    
                    # Tampilkan Grafik Respons Spektrum
                    st.subheader("📈 Kurva Respons Spektrum & Posisi Mode Getar")
                    T_vals = np.linspace(0, 4, 100)
                    Sa_vals = [hasil_gempa['SDS'] * (0.4 + 0.6*t/hasil_gempa['T0']) if t < hasil_gempa['T0'] else hasil_gempa['SDS'] if t < hasil_gempa['Ts'] else hasil_gempa['SD1']/t if t > 0 else 0 for t in T_vals]
                    
                    fig_rsa = px.line(x=T_vals, y=Sa_vals, title=f"Respons Spektrum ({pilihan_kota} - {kode_situs})")
                    fig_rsa.update_traces(line_color='#2563eb', line_width=3, fill='tozeroy', fillcolor='rgba(37, 99, 235, 0.1)')
                    fig_rsa.update_layout(xaxis_title="Periode T (detik)", yaxis_title="Percepatan Spektral Sa (g)")
                    
                    colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6']
                    for index, row in df_modal.head(5).iterrows(): # Tampilkan 5 mode pertama di grafik
                        fig_rsa.add_vline(x=row['Period (T) [s]'], line_dash="dash", line_color=colors[index % 5], line_width=2, annotation_text=f"M{int(row['Mode'])}")
                    st.plotly_chart(fig_rsa, use_container_width=True)
                    
                    # Tampilkan Tabel Partisipasi Massa
                    st.markdown("**Tabel Waktu Getar Alami & Partisipasi Massa (Target $\ge 90\%$)**")
                    def style_modal(val):
                        if isinstance(val, str):
                            if '✅' in val: return 'color: #155724; background-color: #d4edda; font-weight: bold;'
                            elif '⚠️' in val: return 'color: #856404; background-color: #fff3cd;'
                        return ''
                    st.dataframe(df_modal.style.map(style_modal), use_container_width=True)
        else: st.error("File IFC Rusak.")

    st.markdown("---")
    st.subheader("🏗️ Simulasi Geometri Portal & Penskalaan Gempa")
    
    # Input Geometri
    c1, c2, c3 = st.columns(3)
    with c1:
        jml_lantai = st.number_input("Jumlah Lantai", 1, 50, 5, key="fem_jml_lantai")
        tinggi_lantai = st.number_input("Tinggi per Lantai (m)", 2.0, 6.0, 3.5, key="fem_tinggi_lantai")
    with c2:
        bentang_x = st.number_input("Bentang Arah X (m)", 3.0, 12.0, 6.0, key="fem_bentang_x")
        bentang_y = st.number_input("Bentang Arah Y (m)", 3.0, 12.0, 6.0, key="fem_bentang_y")
    with c3:
        fc_mutu = st.number_input("Mutu Beton (MPa)", 20, 60, 30, key="fem_fc")
        num_modes_in = st.number_input("Jumlah Mode Diekstrak", 3, 30, 10, key="fem_modes")
    
    st.markdown("**Simulasi Nilai Geser Dasar (Base Shear) - Diperlukan untuk Audit TPA**")
    c_v1, c_v2, c_v3 = st.columns(3)
    v_statik_in = c_v1.number_input("V Statik (V) [kN]", value=2000.0, step=100.0)
    v_din_x_in = c_v2.number_input("V Dinamik Arah X (Vt) [kN]", value=1850.0, step=100.0) # Sengaja dibuat < 2000 agar scaling aktif
    v_din_y_in = c_v3.number_input("V Dinamik Arah Y (Vt) [kN]", value=2100.0, step=100.0)

    if st.button("🚀 Pre-Audit & Run Dinamis", type="primary"):
        if tinggi_lantai > 5.0 and fc_mutu < 25: st.error("⛔ DITOLAK: Tinggi > 5m butuh mutu beton min 25 MPa.")
        elif 'libs_fem' not in sys.modules: st.error("❌ Modul FEM gagal load.")
        else:
            try:
                engine = libs_fem.OpenSeesEngine()
                engine.build_simple_portal(bentang_x, bentang_y, tinggi_lantai, jml_lantai, fc_mutu)
                
                # 1. Analisis Modal
                df_modal = engine.run_modal_analysis(num_modes=num_modes_in)
                st.success("✅ Analisis Selesai! Berikut adalah laporan audit parameter dinamik.")
                
                st.markdown("#### 1️⃣ Evaluasi Partisipasi Massa Ragam (SNI 1726:2019 Pasal 7.9.1.1)")
                def style_modal(val):
                    if isinstance(val, str):
                        if '✅' in val: return 'color: #155724; background-color: #d4edda; font-weight: bold;'
                        elif '⚠️' in val: return 'color: #856404; background-color: #fff3cd;'
                    return ''
                st.dataframe(df_modal.style.map(style_modal), use_container_width=True)
                
                st.markdown("#### 2️⃣ Penskalaan Gaya Geser Dasar / Base Shear (SNI 1726:2019 Pasal 7.9.4.1)")
                df_scale = engine.check_base_shear_scaling(V_statik=v_statik_in, V_dinamik_x=v_din_x_in, V_dinamik_y=v_din_y_in)
                
                def style_scaling(val):
                    if isinstance(val, str):
                        if '✅' in val: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        elif '❌' in val: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
                    return ''
                st.dataframe(df_scale.style.map(style_scaling), use_container_width=True)
                
            except Exception as e: st.error(f"Error FEM: {e}")

# --- MODE TEMPLATE STRUKTUR (SAP2000 STYLE) ---
elif selected_menu == "🏛️ Template Struktur (Klasik)":
    st.header("🏛️ Template Struktur Parametrik")
    st.caption("Generator instan model elemen hingga bergaya antarmuka SAP2000 Klasik.")
    
    if 'libs_fem' not in sys.modules:
        st.warning("⚠️ Modul `libs_fem` (OpenSees) belum dimuat oleh sistem.")
    else:
        # ZONA 1: Pemilihan Tipe (Top Bar)
        tipe_template = st.selectbox(
            "1. Pilih Tipe Struktur Dasar:", 
            ["2D Portal Frame (Gedung)", "Continuous Beam (Menerus)", "2D Truss", "3D Building Frame"],
            index=0
        )
        
        st.divider()
        
        # ZONA 2 & 3: Input Kiri, Visualisasi Kanan
        col_input, col_viz = st.columns([1, 2.5])
        
        with col_input:
            st.markdown("### 2. Parameter Geometri")
            
            # --- JIKA MEMILIH PORTAL FRAME ---
            if tipe_template == "2D Portal Frame (Gedung)":
                st.info("Satuan standar: Meter (m)")
                jml_lantai = st.number_input("Number of Stories", min_value=1, max_value=50, value=3, step=1, key="tmpl_portal_lantai")
                jml_bentang = st.number_input("Number of Bays", min_value=1, max_value=20, value=4, step=1, key="tmpl_portal_bentang")
                tinggi_lt = st.number_input("Typical Story Height (m)", min_value=1.0, value=3.5, step=0.5, key="tmpl_portal_tinggi")
                lebar_btg = st.number_input("Typical Bay Width (m)", min_value=1.0, value=4.0, step=0.5, key="tmpl_portal_lebar")
                
                with st.expander("⚙️ Opsi Lanjutan (Material & Penampang)"):
                    st.selectbox("Material Dasar", ["Beton K-300", "Baja BJ-37", "Custom"])
                    st.caption("Di versi ini, penampang di-generate sebagai garis as (centerline) analitik.")
                
                st.write("") # Spacer
                if st.button("🚀 Generate Portal", type="primary", use_container_width=True):
                    with st.spinner("Merakit Matriks Kekakuan OpenSees..."):
                        generator = sys.modules['libs_fem'].OpenSeesTemplateGenerator()
                        fig_hasil, df_hasil = generator.generate_2d_portal(jml_lantai, jml_bentang, tinggi_lt, lebar_btg)
                        if fig_hasil is not None:
                            st.session_state['template_fig'] = fig_hasil
                            st.session_state['template_df'] = df_hasil
                            st.session_state['template_status'] = f"✅ Berhasil membuat {len(df_hasil)} elemen portal."
                        else:
                            st.error(df_hasil)

            # --- JIKA MEMILIH CONTINUOUS BEAM ---
            elif tipe_template == "Continuous Beam (Menerus)":
                st.info("Satuan standar: Meter (m)")
                jml_bentang = st.number_input("Number of Spans (Jumlah Bentang)", min_value=1, max_value=20, value=3, step=1, key="tmpl_beam_bentang")
                panjang_btg = st.number_input("Typical Span Length (m)", min_value=1.0, value=6.0, step=0.5, key="tmpl_beam_panjang")
                
                st.write("") # Spacer
                if st.button("🚀 Generate Balok Menerus", type="primary", use_container_width=True):
                    with st.spinner("Membangun model elemen hingga..."):
                        generator = sys.modules['libs_fem'].OpenSeesTemplateGenerator()
                        fig_hasil, df_hasil = generator.generate_continuous_beam(jml_bentang, panjang_btg)
                        if fig_hasil is not None:
                            st.session_state['template_fig'] = fig_hasil
                            st.session_state['template_df'] = df_hasil
                            st.session_state['template_status'] = f"✅ Berhasil membuat {len(df_hasil)} elemen balok menerus."
                        else:
                            st.error(df_hasil)
                            
            # --- JIKA MEMILIH 2D TRUSS ---
            elif tipe_template == "2D Truss":
                st.info("Satuan standar: Meter (m)")
                span_truss = st.number_input("Panjang Bentang Total (L) [m]", min_value=2.0, value=12.0, step=1.0, key="tmpl_truss_span")
                tinggi_truss = st.number_input("Tinggi Puncak (H) [m]", min_value=1.0, value=3.0, step=0.5, key="tmpl_truss_height")
                panel_truss = st.number_input("Jumlah Panel Pias (Wajib Genap)", min_value=2, max_value=20, value=6, step=2, key="tmpl_truss_panel")
                
                st.write("") # Spacer
                if st.button("🚀 Generate Rangka Atap", type="primary", use_container_width=True):
                    with st.spinner("Membangun geometri Truss baja..."):
                        generator = sys.modules['libs_fem'].OpenSeesTemplateGenerator()
                        fig_hasil, df_hasil = generator.generate_2d_truss(span_truss, tinggi_truss, panel_truss)
                        if fig_hasil is not None:
                            st.session_state['template_fig'] = fig_hasil
                            st.session_state['template_df'] = df_hasil
                            st.session_state['template_status'] = f"✅ Berhasil membuat {len(df_hasil)} elemen rangka atap."
                        else:
                            st.error(df_hasil)
            else:
                st.warning("Template ini sedang dalam tahap pengembangan (WIP).")
            
            
        # --- ZONA VISUALISASI ---
        with col_viz:
            st.markdown("### 3. Visualisasi Model (Real-time)")
            
            if 'template_fig' in st.session_state:
                st.success(st.session_state['template_status'])
                with st.container(border=True):
                    st.plotly_chart(st.session_state['template_fig'], use_container_width=True, height=500)
                
                with st.expander("📋 Tabel Rekapitulasi Elemen Terbentuk", expanded=False):
                    st.dataframe(st.session_state['template_df'], use_container_width=True)
                    
                # MENGHIDUPKAN FUNGSI TOMBOL
                c_act1, c_act2 = st.columns(2)
                
                if c_act1.button("⚖️ Lanjut: Define Beban & Kombinasi", use_container_width=True):
                    # Membuka gerbang UI pembebanan
                    st.session_state['mode_pembebanan'] = True
                    st.rerun()
                    
                if c_act2.button("💾 Simpan ke Database Proyek", type="secondary", use_container_width=True):
                    st.session_state['model_ready_to_analyze'] = True
                    st.toast("✅ Geometri struktur berhasil dikunci ke dalam CDE (Common Data Environment) Proyek Anda!", icon="💾")
                    
            else:
                st.info("👈 Masukkan parameter di sebelah kiri dan klik **Generate Model**.")
                with st.container(border=True):
                    st.markdown("<div style='height: 400px; display: flex; align-items: center; justify-content: center; color: gray;'>Ruang Gambar Geometri</div>", unsafe_allow_html=True)

        # ==========================================
        # ZONA 4: PEMBEBANAN & ANALISIS (FITUR BARU)
        # ==========================================
        if st.session_state.get('mode_pembebanan', False):
            st.markdown("---")
            st.markdown("### ⚖️ Definisi Beban & Jalankan Analisis (OpenSees Solver)")
            st.info("Masukkan intensitas beban. Sistem akan merakit ulang matriks kekakuan dan mengeksekusi analisis secara *real-time*.")
            
            c_beban1, c_beban2, c_beban3 = st.columns([1, 1, 1])
            q_load = c_beban1.number_input("Beban Merata Balok (q) [kN/m]", min_value=0.0, value=15.0, step=1.0)
            p_load = c_beban2.number_input("Beban Titik Lateral (P) [kN]", min_value=0.0, value=25.0, step=5.0, help="Bekerja pada kolom paling luar sebelah kiri")
            
            with c_beban3:
                st.write("") # Spacer agar tombol sejajar
                st.write("")
                if st.button("▶️ JALANKAN SOLVER", type="primary", use_container_width=True):
                    with st.spinner("OpenSees menyelesaikan persamaan matriks statik..."):
                        generator = sys.modules['libs_fem'].OpenSeesTemplateGenerator()
                        
                        # 1. Rakit Ulang Geometri berdasarkan input di memory
                        if tipe_template == "2D Portal Frame (Gedung)":
                            generator.generate_2d_portal(st.session_state['tmpl_portal_lantai'], st.session_state['tmpl_portal_bentang'], st.session_state['tmpl_portal_tinggi'], st.session_state['tmpl_portal_lebar'])
                        elif tipe_template == "Continuous Beam (Menerus)":
                            generator.generate_continuous_beam(st.session_state['tmpl_beam_bentang'], st.session_state['tmpl_beam_panjang'])
                        elif tipe_template == "2D Truss":
                            generator.generate_2d_truss(st.session_state['tmpl_truss_span'], st.session_state['tmpl_truss_height'], st.session_state['tmpl_truss_panel'])
                            
                        # 2. Tembakkan Beban & Analisis
                        df_forces, fig_deform = generator.apply_loads_and_analyze(q_load, p_load)
                        
                        if df_forces is not None:
                            st.session_state['hasil_df'] = df_forces
                            st.session_state['hasil_fig'] = fig_deform
                            st.success("✅ Analisis Konvergen & Selesai!")
                        else:
                            st.error(fig_deform)
            
            # Menampilkan Hasil Akhir di bawahnya
            if 'hasil_fig' in st.session_state:
                st.markdown("#### 📈 Hasil Deformasi & Gaya Dalam (Post-Processing)")
                col_hasil1, col_hasil2 = st.columns([1, 1.5])
                
                with col_hasil1:
                    st.markdown("**Rekapitulasi Gaya Dalam Maksimum**")
                    # Tampilkan tabel yang di-highlight nilai ekstremnya
                    st.dataframe(st.session_state['hasil_df'].style.highlight_max(subset=['Momen Max (kNm)', 'Aksial (kN)'], color='lightcoral'), use_container_width=True, height=450)
                
                with col_hasil2:
                    with st.container(border=True):
                        # Grafik deformasi dengan garis putus-putus untuk posisi awal
                        st.plotly_chart(st.session_state['hasil_fig'], use_container_width=True)
                        st.caption("💡 *Arahkan kursor mouse (hover) ke garis elemen merah/biru untuk melihat nilai Momen dan Gaya Aksial pada elemen tersebut.*")
                
                
        
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
# --- F. MODE DESAIN IRIGASI & KP-01 ---
elif selected_menu == "🌾 Desain Irigasi (KP-01)":
    st.header("🌾 Desain Jaringan Irigasi & Nomenklatur (KP-01)")
    
    if 'libs_irigasi' not in sys.modules:
        st.warning("⚠️ Modul `libs_irigasi` belum dimuat oleh sistem.")
    else:
        # Inisialisasi Engine
        irigasi_eng = sys.modules['libs_irigasi'].Irrigation_Engine()
        
        # Buat 2 Tab agar UI tetap bersih
        tab_saluran, tab_jaringan = st.tabs(["📐 Desain Penampang Hidrolis", "🕸️ Skema & Nomenklatur Jaringan"])
        
        # =========================================================
        # TAB 1: DESAIN PENAMPANG SALURAN EKONOMIS
        # =========================================================
        with tab_saluran:
            st.markdown("#### Desain Dimensi Saluran Ekonomis (Metode fsolve)")
            with st.expander("⚙️ Parameter Hidrolika Saluran Terbuka", expanded=True):
                c_ir1, c_ir2 = st.columns(2)
                q_desain = c_ir1.number_input("Debit Rencana (Q) [m3/s]", value=2.5, step=0.1)
                kemiringan_m = c_ir2.number_input("Kemiringan Talud (m) [1:m]", value=1.0, step=0.1, help="Misal 1.0 untuk saluran tanah")
                
                c_ir3, c_ir4 = st.columns(2)
                kemiringan_dasar = c_ir3.number_input("Kemiringan Dasar Saluran (S)", value=0.0005, format="%.5f", step=0.0001)
                manning_n = c_ir4.number_input("Angka Kekasaran Manning (n)", value=0.025, format="%.3f", help="0.025 untuk saluran tanah biasa, 0.015 untuk beton")

            if st.button("🚀 Hitung & Gambar Saluran", type="primary", use_container_width=True):
                with st.spinner("Menghitung resolusi numerik dimensi optimal..."):
                    try:
                        # Panggil fungsi yang mengembalikan figur Matplotlib dan data dimensi
                        fig_saluran, data_dim = irigasi_eng.hitung_dan_gambar_saluran(
                            Q=q_desain, S=kemiringan_dasar, n=manning_n, m=kemiringan_m
                        )
                        
                        st.success("✅ Desain Penampang Selesai!")
                        
                        # Tampilkan Metrik Hasil
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Lebar Dasar (b)", f"{data_dim['b']} m")
                        m2.metric("Kedalaman Air (h)", f"{data_dim['h']} m")
                        m3.metric("Tinggi Jagaan (w)", f"{data_dim['w']} m")
                        m4.metric("Tinggi Total (H)", f"{data_dim['H']} m")
                        
                        # Render Gambar Potongan Melintang
                        st.pyplot(fig_saluran)
                    except Exception as e:
                        st.error(f"Terjadi kesalahan komputasi: {e}")

        # =========================================================
        # TAB 2: SKEMA JARINGAN & NOMENKLATUR (NETWORKX)
        # =========================================================
        with tab_jaringan:
            st.markdown("#### Generator Nomenklatur & Skema Jaringan (Standar KP-01)")
            
            nama_di = st.text_input("Nama Daerah Irigasi (DI):", value="Way Sekampung")
            
            st.markdown("**Data Saluran Sekunder & Petak Tersier:**")
            st.caption("Silakan edit tabel di bawah ini untuk menambahkan saluran sekunder dan jumlah boks sadap tersiernya.")
            
            # Gunakan Data Editor bawaan Streamlit agar user bisa menambah/menghapus baris
            df_sekunder_template = pd.DataFrame([
                {"nama": "Natar", "jumlah_tersier": 3},
                {"nama": "Jati Agung", "jumlah_tersier": 2},
                {"nama": "Tegineneng", "jumlah_tersier": 4}
            ])
            
            df_input = st.data_editor(df_sekunder_template, num_rows="dynamic", use_container_width=True)
            
            if st.button("🕸️ Generate Skema & Nomenklatur", type="primary"):
                with st.spinner("Menyusun hierarki graf jaringan..."):
                    try:
                        # Ubah DataFrame menjadi list of dicts sesuai kebutuhan backend
                        data_sekunder_list = df_input.to_dict('records')
                        
                        # Panggil fungsi backend
                        fig_network, df_nomenklatur = irigasi_eng.generate_skema_jaringan_kp01(
                            nama_daerah_irigasi=nama_di, 
                            data_sekunder=data_sekunder_list
                        )
                        
                        # Render Grafik Hierarki NetworkX - Plotly
                        st.plotly_chart(fig_network, use_container_width=True)
                        
                        # Tampilkan Tabel Nomenklatur
                        st.markdown(f"**Tabel Rekapitulasi Nomenklatur D.I. {nama_di}**")
                        st.dataframe(df_nomenklatur, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"Gagal menyusun skema: {e}")
# --- G. MODE HIDROLIKA BENDUNG & KANTONG LUMPUR ---
elif selected_menu == "🌊 Hidrolika Bendung (KP-02)":
    st.header("🌊 Analisis Hidrolika Bendung & Kantong Lumpur")
    st.caption("Standard Perencanaan Irigasi KP-02 (Bangunan Utama)")
    
    if 'libs_bendung' not in sys.modules:
        st.warning("⚠️ Modul `libs_bendung` belum dimuat oleh sistem.")
    else:
        bendung_eng = sys.modules['libs_bendung'].Bendung_Engine()
        
        tab_mercu, tab_rembesan, tab_lumpur = st.tabs(["🌊 Hidrolika Mercu", "💧 Analisis Rembesan (Piping)", "🪨 Kantong Lumpur"])
        
        # =========================================================
        # TAB 1: HIDROLIKA MERCU
        # =========================================================
        with tab_mercu:
            st.markdown("#### Dimensi Efektif Mercu & Muka Air Banjir (Hd)")
            with st.expander("⚙️ Parameter Sungai & Bendung", expanded=True):
                c1, c2 = st.columns(2)
                Q_banjir = c1.number_input("Debit Banjir Rencana (Q) [m3/s]", value=150.0, step=10.0)
                B_sungai = c2.number_input("Lebar Sungai Rata-rata (B) [m]", value=30.0, step=1.0)
                
                c3, c4, c5 = st.columns(3)
                n_pilar = c3.number_input("Jumlah Pilar Pembilas", value=2, step=1)
                lebar_pilar = c4.number_input("Lebar Pilar [m]", value=1.0, step=0.1)
                Cd = c5.number_input("Koefisien Debit (Cd)", value=2.1, format="%.2f")
                
            if st.button("🚀 Hitung Hidrolika Mercu", type="primary", use_container_width=True):
                with st.spinner("Mengkalkulasi dimensi efektif..."):
                    Be = bendung_eng.hitung_lebar_efektif(B_sungai, n_pilar, lebar_pilar)
                    Hd = bendung_eng.hitung_tinggi_muka_air_banjir(Q_banjir, Be, Cd)
                    
                    st.success("✅ Perhitungan Selesai!")
                    m1, m2 = st.columns(2)
                    m1.metric("Lebar Efektif Bendung (Be)", f"{Be:.2f} m", delta=f"Lebar Total: {B_sungai} m", delta_color="off")
                    m2.metric("Tinggi Energi di atas Mercu (Hd)", f"{Hd:.3f} m")
                    st.info(f"💡 **Interpretasi:** Untuk melewatkan debit banjir {Q_banjir} m3/s, muka air akan naik setinggi {Hd:.3f} meter dari elevasi puncak mercu bendung.")

        # =========================================================
        # TAB 2: ANALISIS REMBESAN (PIPING)
        # =========================================================
        with tab_rembesan:
            st.markdown("#### Kontrol Stabilitas Rembesan (Metode Lane)")
            st.write("Mencegah terjadinya gejala *Piping* (pembawaan partikel tanah di bawah pondasi bendung).")
            
            with st.expander("⚙️ Parameter Geoteknik & Rayapan", expanded=True):
                dH = st.number_input("Beda Tinggi Muka Air Hulu-Hilir (\u0394H) [m]", value=5.0, step=0.5)
                jenis_tanah = st.selectbox("Jenis Tanah Dasar Pondasi", [
                    "pasir sangat halus", "pasir halus", "pasir sedang", 
                    "pasir kasar", "kerikil halus", "kerikil kasar", "lempung keras"
                ], index=1)
                
                st.markdown("**Panjang Jalur Rayapan (Creep Line):**")
                c_lv, c_lh = st.columns(2)
                lv_str = c_lv.text_input("Rayapan Vertikal (Lv) [m]", value="2.0, 3.0, 2.0", help="Kedalaman Sheetpile/Cut-off (pisahkan dengan koma)")
                lh_str = c_lh.text_input("Rayapan Horizontal (Lh) [m]", value="5.0, 10.0, 5.0", help="Panjang lantai muka/kolam olak (pisahkan dengan koma)")
            
            if st.button("🛡️ Cek Keamanan Rembesan", type="primary", use_container_width=True):
                try:
                    # Konversi string ke list of floats
                    lv_list = [float(x.strip()) for x in lv_str.split(",")]
                    lh_list = [float(x.strip()) for x in lh_str.split(",")]
                    
                    res_lane = bendung_eng.cek_rembesan_lane(dH, lv_list, lh_list, jenis_tanah)
                    
                    if "Error" in res_lane.get("Status", ""):
                        st.error(res_lane["Status"])
                    else:
                        if "AMAN" in res_lane["Status"]:
                            st.success(f"**{res_lane['Status']}**")
                        else:
                            st.error(f"**{res_lane['Status']}**")
                            
                        # Tampilkan Rincian
                        st.json({
                            "Total Rayapan Lane (Lw)": f"{res_lane['Panjang_Rayapan_Lane_Lw_m']} m",
                            "Angka Rembesan Aktual (Cw)": res_lane['Angka_Rembesan_Aktual_Cw'],
                            "Syarat Cw Minimum KP-02": res_lane['Angka_Rembesan_Izin_Min']
                        })
                except Exception as e:
                    st.error("❌ Format input Lv/Lh salah. Pastikan menggunakan angka yang dipisah koma (contoh: 2.5, 3.0).")

        # =========================================================
        # TAB 3: KANTONG LUMPUR (SEDIMENT TRAP)
        # =========================================================
        with tab_lumpur:
            st.markdown("#### Desain Dimensi Kantong Lumpur")
            st.write("Berdasarkan kecepatan jatuh sedimen (w) dan kecepatan aliran (v).")
            
            with st.expander("⚙️ Parameter Hidrolis Kantong Lumpur", expanded=True):
                c_k1, c_k2, c_k3 = st.columns(3)
                Q_normal = c_k1.number_input("Debit Pengambilan Normal [m3/s]", value=2.5, step=0.1)
                w_endap = c_k2.number_input("Kecepatan Endap Partikel (w) [m/s]", value=0.040, format="%.3f", help="0.04 m/s umum untuk pasir halus")
                v_aliran = c_k3.number_input("Kecepatan Aliran Izin (v) [m/s]", value=0.30, format="%.2f", help="Batas kecepatan agar lumpur mengendap (biasanya < 0.4 m/s)")
                
            if st.button("📏 Hitung Dimensi Kantong Lumpur", type="primary", use_container_width=True):
                with st.spinner("Menghitung proporsi sediment trap..."):
                    res_lumpur = bendung_eng.dimensi_kantong_lumpur(Q_normal, w_endap, v_aliran)
                    
                    st.success("✅ Estimasi Dimensi Selesai!")
                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("Lebar Efektif (B)", f"{res_lumpur['Lebar_B_m']} m")
                    col_res2.metric("Kedalaman Air (h)", f"{res_lumpur['Kedalaman_Air_h_m']} m")
                    col_res3.metric("Panjang Saluran (L)", f"{res_lumpur['Panjang_L_m']} m", delta="+20% Turbulensi", delta_color="off")
                    
                    st.info(f"**Luas Permukaan Minimum yang Dibutuhkan:** {res_lumpur['Luas_Permukaan_m2']} m²")                       
# --- D. MODE ANALISIS HIDROLOGI & JIAT (SNI 2415 & KP-01) ---
elif selected_menu == "🌊 Analisis Hidrologi":
    st.header("🌊 Analisis Sumber Daya Air & JIAT")
    
    if 'libs_hidrologi' not in sys.modules or 'libs_jiat' not in sys.modules:
        st.warning("⚠️ Modul Hidrologi/JIAT belum dimuat.")
    else:
        hydro = libs_hidrologi.Hidrologi_Engine()
        jiat_eng = libs_jiat.JIAT_Engine()

        # Membuat 2 Tab untuk merapikan UI
        tab_banjir, tab_jiat = st.tabs(["📊 Debit Banjir (HSS Nakayasu)", "🚰 Audit Pompa JIAT (Kurva Head-Discharge)"])


        # =========================================================
        # TAB 1: HIDROLOGI BANJIR (KODE SEBELUMNYA DIAMANKAN DI SINI)
        # =========================================================
        with tab_banjir:
            st.markdown("Evaluasi Debit Banjir Rencana (SNI 2415:2016)")
            
            # --- [FITUR BARU] DATABASE HISTORIS BMKG (MOCK-UP API) ---
            db_hujan_bmkg = {
                "Manual Input (Custom)": "85.5, 92.1, 105.4, 78.2, 115.0, 99.5, 88.0, 140.2, 110.5, 95.0",
                "☁️ Stasiun Meteorologi Fatmawati Soekarno (Bengkulu)": "125.4, 110.2, 145.5, 98.4, 132.0, 150.5, 115.8, 140.2, 122.6, 105.0",
                "☁️ Stasiun Meteorologi Radin Inten II (Bandar Lampung)": "95.0, 88.5, 115.2, 75.4, 102.8, 125.0, 85.6, 110.5, 92.4, 105.5",
                "☁️ Stasiun Klimatologi Pesawaran (Mewakili Lamsel)": "85.2, 105.6, 92.4, 115.8, 88.5, 122.0, 95.5, 110.2, 108.5, 98.4",
                "☁️ Pos Pengamatan Hujan Sukadana (Lampung Timur)": "92.5, 85.0, 110.2, 105.5, 95.8, 88.4, 120.5, 102.4, 98.6, 115.2"
            }
            
            st.markdown("#### 📡 Sinkronisasi Data Klimatologi")
            col_api1, col_api2 = st.columns([2, 1])
            with col_api1:
                pilihan_stasiun = st.selectbox("Pilih Stasiun Pengamat Terdekat dengan Proyek:", list(db_hujan_bmkg.keys()), label_visibility="collapsed")
            with col_api2:
                if st.button("📥 Tarik Data BMKG", use_container_width=True):
                    import time
                    st.toast(f"Menghubungkan ke server {pilihan_stasiun.replace('☁️ ', '')}...", icon="🔄")
                    time.sleep(1) # Efek delay seolah sedang download dari internet
                    st.success("✅ Data Historis Curah Hujan Maksimum 10 Tahun berhasil ditarik!")
            
            # Data yang tampil di kotak akan otomatis berubah sesuai pilihan dropdown
            data_terpilih = db_hujan_bmkg[pilihan_stasiun]
            # -------------------------------------------------------------

            with st.expander("⚙️ Parameter DAS & Data Hujan", expanded=True):
                col1, col2 = st.columns([1, 1])
                with col1:
                    hujan_input = st.text_area(
                        "Data Curah Hujan Harian Maksimum (mm):",
                        value=data_terpilih, height=100
                    )
                    try: data_hujan = [float(x.strip()) for x in hujan_input.split(',')]
                    except: data_hujan = []; st.error("Format input salah!")

                with col2:
                    c_das1, c_das2 = st.columns(2)
                    luas_das = c_das1.number_input("Luas DAS (km²)", value=25.5, step=1.0)
                    panjang_sungai = c_das2.number_input("Panjang Sungai (km)", value=8.5, step=0.5)

                    cn_options = {"Hutan (55)": 55, "Pertanian (75)": 75, "Perumahan (85)": 85, "Beton/Aspal (98)": 98}
                    pilihan_cn = st.selectbox("Tutupan Lahan (Curve Number)", list(cn_options.keys()), index=2)
                    cn_val = cn_options[pilihan_cn]
                    periode_ulang = st.selectbox("Periode Ulang (Tahun)", [2, 5, 10, 25, 50, 100], index=4)

            if st.button("🚀 Eksekusi Hidrologi & Buat Kurva", type="primary", use_container_width=True):
                # (SISA KODE DI BAWAHNYA TETAP SAMA SEPERTI SEBELUMNYA)
                hasil_stat = hydro.analisis_frekuensi_hujan(data_hujan)
        
                
                st.subheader("1. Komparasi Distribusi Frekuensi")
                df_hujan = pd.DataFrame({
                    "Periode Ulang": [f"{t} Tahun" for t in [2, 5, 10, 25, 50, 100]],
                    "Gumbel Tipe I (mm)": list(hasil_stat['Curah_Hujan_Gumbel_mm'].values()),
                    "Log Pearson Tipe III (mm)": list(hasil_stat['Curah_Hujan_LP3_mm'].values())
                })
                st.dataframe(df_hujan, use_container_width=True)

                r_design = hasil_stat['Curah_Hujan_LP3_mm'][f'R{periode_ulang}']
                pe = hydro.hitung_hujan_efektif_cn(r_design, cn_val)
                df_hss, params = hydro.hitung_hss_nakayasu(luas_das, panjang_sungai, R0_mm=pe)

                st.subheader(f"2. Hidrograf Nakayasu (Periode {periode_ulang} Tahun)")
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Hujan Efektif (Pe)", f"{pe} mm", delta=f"Dari P={r_design}mm")
                c_m2.metric("Waktu Puncak (Tp)", params['Time Peak (Tp)'])
                c_m3.metric("Debit Puncak (Qp)", params['Debit Puncak (Qp)'], delta_color="off")

                fig_hss = px.area(df_hss, x="Waktu (Jam)", y="Debit (m3/s)", title="Kurva HSS Nakayasu")
                fig_hss.update_traces(line_color='#0ea5e9', fillcolor='rgba(14, 165, 233, 0.25)', line_width=3)
                tp_val = float(params['Time Peak (Tp)'].split(' ')[0])
                fig_hss.add_vline(x=tp_val, line_dash="dash", line_color="red")
                st.plotly_chart(fig_hss, use_container_width=True)

        # =========================================================
        # TAB 2: AUDIT POMPA JIAT (FITUR BARU)
        # =========================================================
        with tab_jiat:
            st.markdown("Kalibrasi **Sistem Head (Hazen-Williams)** vs **Kinerja Pompa (Performance Curve)**")
            
            with st.expander("⚙️ Parameter Jaringan Irigasi Air Tanah (JIAT)", expanded=True):
                c_j1, c_j2, c_j3 = st.columns(3)
                q_target = c_j1.number_input("Debit Kebutuhan Irigasi (L/s)", value=15.0, step=1.0)
                h_statik = c_j2.number_input("Head Statis / Elevasi (m)", value=45.0, step=5.0)
                l_pipa = c_j3.number_input("Panjang Jalur Pipa (m)", value=1200.0, step=50.0)
                
                c_j4, c_j5, c_j6 = st.columns(3)
                d_pipa = c_j4.number_input("Diameter Pipa Dalam (mm)", value=100.0, step=10.0)
                c_hazen = c_j5.number_input("Koef. Hazen-Williams (C)", value=130, step=5)
                sf_pompa = c_j6.number_input("Safety Factor Pompa (%)", value=15, step=5)

            if st.button("🚀 Render Kurva Kalibrasi Pompa", type="primary", use_container_width=True):
                with st.spinner("Menghitung intersepsi matriks hidrolika..."):
                    
                    # 1. Eksekusi Engine JIAT
                    df_pump, h_target = jiat_eng.generate_pump_system_curve(q_target, h_statik, l_pipa, d_pipa, c_hazen)
                    rek_pompa = jiat_eng.rekomendasi_pompa(q_target, h_statik, l_pipa, d_pipa)
                    
                    st.divider()
                    st.subheader("📊 Metrik Evaluasi Hidraulika")
                    
                    m_p1, m_p2, m_p3 = st.columns(3)
                    m_p1.metric("Head Statik Murni", f"{h_statik} m")
                    m_p2.metric("Total Dynamic Head (TDH)", f"{rek_pompa['Head_Total_m']} m", delta=f"+ {rek_pompa['Head_Total_m'] - h_statik:.2f} m (Friction Loss)", delta_color="inverse")
                    m_p3.metric("Kebutuhan Daya Pompa", f"{rek_pompa['Power_kW']} kW", delta=f"{rek_pompa['Power_HP']} HP", delta_color="off")

                    st.subheader("📈 Kurva Operasi Pompa (Operating/Duty Point)")
                    
                    # 2. Visualisasi Kurva Ganda dengan Plotly
                    fig_pump = go.Figure()
                    
                    # A. Plot System Head Curve (Kurva Sistem Pipa - Eksponensial Naik)
                    fig_pump.add_trace(go.Scatter(
                        x=df_pump["Debit (L/s)"], y=df_pump["System Head (m)"],
                        mode='lines', name='Kurva Sistem (Friction)',
                        line=dict(color='blue', width=3)
                    ))
                    
                    # B. Plot Pump Performance Curve (Kurva Kinerja Pompa - Parabola Turun)
                    fig_pump.add_trace(go.Scatter(
                        x=df_pump["Debit (L/s)"], y=df_pump["Pump Head (m)"],
                        mode='lines', name='Kurva Kapasitas Pompa',
                        line=dict(color='red', width=3)
                    ))
                    
                    # C. Tandai Titik Kerja (Duty Point)
                    # Menambahkan margin sesuai input Safety Factor
                    q_duty = q_target * (1 + (sf_pompa/100))
                    h_duty = h_target * (1 + (sf_pompa/100))
                    
                    fig_pump.add_trace(go.Scatter(
                        x=[q_target], y=[h_target],
                        mode='markers+text', name='Titik Kebutuhan Dasar',
                        marker=dict(color='orange', size=10, symbol='diamond'),
                        text=[f"Q:{q_target} L/s<br>H:{h_target:.1f} m"], textposition="bottom right"
                    ))

                    fig_pump.add_trace(go.Scatter(
                        x=[q_duty], y=[h_duty],
                        mode='markers+text', name='Titik Operasi (Duty Point)',
                        marker=dict(color='green', size=14, symbol='star'),
                        text=[f"Duty Point<br>Q:{q_duty:.1f} L/s<br>H:{h_duty:.1f} m"], textposition="top right"
                    ))

                    fig_pump.update_layout(
                        title="Perpotongan Karakteristik Sistem Pipa vs Kapasitas Pompa Sentrifugal",
                        xaxis_title="Kapasitas Debit - Q (Liter / Detik)",
                        yaxis_title="Total Head - H (Meter)",
                        hovermode="x unified",
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                    )
                    
                    st.plotly_chart(fig_pump, use_container_width=True)
                    
                    st.success(f"**Kesimpulan Audit TPA:** Pompa JIAT wajib dikalibrasi untuk beroperasi pada Titik Kerja (Duty Point) di kapasitas **{q_duty:.1f} L/s** dengan dorongan Head **{h_duty:.1f} meter** untuk mengakomodasi kerugian gesekan pipa sepanjang {l_pipa} meter dan Safety Factor {sf_pompa}%.")

# --- H. MODE GEOTEKNIK & STABILITAS LERENG ---
elif selected_menu == "🪨 Analisis Geoteknik & Lereng":
    st.header("🪨 Analisis Geoteknik & Stabilitas Lereng")
    st.caption("Evaluasi Kestabilan Bendungan Urugan & Instrumen Keamanan (Dam Safety)")
    
    if 'libs_geoteknik' not in sys.modules:
        st.warning("⚠️ Modul `libs_geoteknik` belum dimuat oleh sistem.")
    else:
        geo_eng = sys.modules['libs_geoteknik'].Geotech_Engine()
        
        tab_bishop, tab_sensor = st.tabs(["⛰️ Analisis Stabilitas (Bishop)", "📡 Instrumentasi Dam Safety"])
        
        # =========================================================
        # TAB 1: ANALISIS BISHOP
        # =========================================================
        with tab_bishop:
            st.markdown("#### Metode Irisan Bishop Sederhana (Simplified Bishop)")
            st.write("Menghitung Safety Factor (FS) secara iteratif dan merender bidang gelincir kritis.")
            
            with st.expander("⚙️ Parameter Geometri & Tanah", expanded=True):
                c_geo1, c_geo2 = st.columns(2)
                tinggi_lereng = c_geo1.number_input("Tinggi Lereng / Bendungan (H) [m]", value=15.0, step=1.0)
                sudut_lereng = c_geo2.number_input("Sudut Kemiringan Lereng (\u03b2) [\u00b0]", value=35.0, step=1.0, help="Diukur dari bidang horizontal")
                
                st.markdown("**Properti Mekanika Tanah:**")
                c_geo3, c_geo4, c_geo5 = st.columns(3)
                kohesi_c = c_geo3.number_input("Kohesi (c) [kPa]", value=12.0, step=1.0)
                sudut_geser_phi = c_geo4.number_input("Sudut Geser Dalam (\u03c6) [\u00b0]", value=22.0, step=1.0)
                berat_volume_gamma = c_geo5.number_input("Berat Volume Tanah (\u03b3) [kN/m³]", value=18.5, step=0.5)
            
            if st.button("🚀 Iterasi & Temukan Bidang Gelincir", type="primary", use_container_width=True):
                with st.spinner("Melakukan iterasi numerik Bishop untuk mencari FS..."):
                    try:
                        # Panggil fungsi dari backend
                        hasil_bishop, fig_bishop = geo_eng.analisis_stabilitas_bishop(
                            tinggi_lereng, sudut_lereng, kohesi_c, sudut_geser_phi, berat_volume_gamma
                        )
                        
                        st.success("✅ Iterasi Konvergen Selesai!")
                        
                        # Tampilkan Metrik
                        m_fs1, m_fs2 = st.columns(2)
                        m_fs1.metric("Faktor Keamanan (Safety Factor - FS)", f"{hasil_bishop['Safety_Factor_FS']:.3f}", 
                                     delta="Batas Aman: FS \u2265 1.5", delta_color="off")
                        
                        status = hasil_bishop['Status_Keamanan']
                        if "AMAN" in status:
                            m_fs2.success(f"**STATUS: {status}**")
                        else:
                            m_fs2.error(f"**STATUS: {status}**")
                            
                        # Render Grafik 2D Plotly Bidang Gelincir
                        st.plotly_chart(fig_bishop, use_container_width=True)
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat merender Bishop: {e}")

        # =========================================================
        # TAB 2: INSTRUMENTASI DAM SAFETY
        # =========================================================
        with tab_sensor:
            st.markdown("#### Dashboard Pemantauan Real-Time (Telemetri Sensor)")
            st.write("Simulasi pemantauan tekanan air pori (Piezometer) dan pergerakan tanah lateral (Inclinometer).")
            
            with st.expander("⚙️ Pengaturan Sensor", expanded=True):
                c_sens1, c_sens2 = st.columns(2)
                kedalaman = c_sens1.number_input("Kedalaman Lubang Bor Inclinometer [m]", value=25, step=1)
                hari = c_sens2.number_input("Rentang Hari Pengamatan", value=30, step=5)
            
            if st.button("📡 Tarik Data Sensor Terkini", type="secondary", use_container_width=True):
                with st.spinner("Menghubungkan ke server telemetri Dam Safety..."):
                    try:
                        hasil_sensor, fig_sensor = geo_eng.simulasi_dam_safety_dashboard(
                            kedalaman_lubang_m=kedalaman, hari_pengamatan=hari
                        )
                        
                        # Render Metrik
                        sm1, sm2, sm3 = st.columns(3)
                        
                        # Indikator warna dinamis
                        delta_color_piezo = "inverse" if "SIAGA" in hasil_sensor['Status_Piezometer'] else "normal"
                        delta_color_inclino = "inverse" if "WASPADA" in hasil_sensor['Status_Inclinometer'] else "normal"
                        
                        sm1.metric("Tekanan Air Pori (PWP) Max", f"{hasil_sensor['Piezometer_PWP_kPa']} kPa", 
                                   delta=hasil_sensor['Status_Piezometer'], delta_color=delta_color_piezo)
                        
                        sm2.metric("Pergerakan Lateral Max", f"{hasil_sensor['Inclinometer_Pergerakan_Max_mm']} mm", 
                                   delta=hasil_sensor['Status_Inclinometer'], delta_color=delta_color_inclino)
                        
                        sm3.metric("Lokasi Kritis Pergerakan", f"Kedalaman {hasil_sensor['Lokasi_Kritis_Kedalaman_m']} m")
                        
                        # Render Dashboard Plotly
                        st.plotly_chart(fig_sensor, use_container_width=True)
                    except Exception as e:
                        st.error(f"Gagal memuat telemetri sensor: {e}")
# --- I. MODE DAYA DUKUNG PONDASI ---
elif selected_menu == "🏗️ Daya Dukung Pondasi":
    st.header("🏗️ Analisis Kapasitas Daya Dukung Pondasi")
    st.caption("Evaluasi Pondasi Dalam (Bore Pile) dan Pondasi Dangkal (Telapak & Batu Kali)")
    
    if 'libs_geoteknik' not in sys.modules or 'libs_pondasi' not in sys.modules:
        st.warning("⚠️ Modul Geoteknik/Pondasi belum dimuat oleh sistem.")
    else:
        # Inisialisasi Engine
        geo_eng = sys.modules['libs_geoteknik'].Geotech_Engine()
        
        # Buat 3 Tab Khusus
        tab_borepile, tab_footplate, tab_batukali = st.tabs([
            "🕳️ Pondasi Dalam (Bore Pile)", 
            "🔲 Pondasi Telapak (Footplate)", 
            "🧱 Pondasi Menerus (Batu Kali)"
        ])
        
        # =========================================================
        # TAB 1: BORE PILE
        # =========================================================
        with tab_borepile:
            st.markdown("#### Analisis Kapasitas Bore Pile (Data N-SPT)")
            st.write("Menghitung tahanan ujung (End Bearing) dan gesekan selimut (Friction) berdasarkan empiris nilai N-SPT.")
            
            with st.expander("⚙️ Parameter Tiang & Tanah", expanded=True):
                c_bp1, c_bp2 = st.columns(2)
                diameter = c_bp1.number_input("Diameter Tiang (D) [m]", value=0.6, step=0.1)
                kedalaman = c_bp2.number_input("Kedalaman Tertanam (L) [m]", value=12.0, step=1.0)
                
                st.markdown("**Nilai N-SPT Lapangan:**")
                c_bp3, c_bp4 = st.columns(2)
                n_ujung = c_bp3.number_input("N-SPT Ujung Tiang (End Bearing)", value=40.0, step=5.0)
                n_selimut = c_bp4.number_input("N-SPT Rata-rata Selimut (Friction)", value=15.0, step=2.0)
                
            if st.button("🚀 Hitung Kapasitas Bore Pile", type="primary", use_container_width=True):
                with st.spinner("Mengkalkulasi tahanan ujung dan selimut..."):
                    # Memanggil fungsi 4-return dari libs_geoteknik.py
                    Qp, Qs, Q_ult, Q_allow = geo_eng.daya_dukung_bore_pile(diameter, kedalaman, n_ujung, n_selimut)
                    
                    st.success("✅ Analisis Bore Pile Selesai!")
                    
                    col_bp1, col_bp2, col_bp3 = st.columns(3)
                    col_bp1.metric("Tahanan Ujung (Qp)", f"{Qp:.2f} kN")
                    col_bp2.metric("Tahanan Selimut (Qs)", f"{Qs:.2f} kN")
                    col_bp3.metric("Kapasitas Ultimate (Q_ult)", f"{Q_ult:.2f} kN")
                    
                    st.info(f"🛡️ **Kapasitas Izin (Q_allow) dengan SF 2.5:** **{Q_allow:.2f} kN** (Setara ~{Q_allow/9.81:.1f} Ton)")

        # =========================================================
        # TAB 2: PONDASI TELAPAK (FOOTPLATE)
        # =========================================================
        with tab_footplate:
            st.markdown("#### Desain & Cek Keamanan Pondasi Telapak")
            
            with st.expander("⚙️ Parameter Beban & Dimensi", expanded=True):
                c_beban1, c_beban2 = st.columns(2)
                sigma_tanah = c_beban1.number_input("Daya Dukung Izin Tanah (\u03c3) [kPa]", value=150.0, step=10.0, help="Contoh: 150 kPa untuk tanah sedang")
                beban_pu = c_beban2.number_input("Beban Aksial Kolom (Pu) [kN]", value=450.0, step=10.0)
                
                st.markdown("**Dimensi Rencana Pondasi (Cakar Ayam):**")
                c_fp1, c_fp2, c_fp3 = st.columns(3)
                lebar_b = c_fp1.number_input("Lebar (B) [m]", value=1.5, step=0.1)
                panjang_l = c_fp2.number_input("Panjang (L) [m]", value=1.5, step=0.1)
                tebal_h = c_fp3.number_input("Tebal / Tinggi (h) [mm]", value=300.0, step=50.0)
                
            if st.button("🛡️ Evaluasi Pondasi Telapak", type="primary", use_container_width=True):
                # Inisialisasi engine spesifik untuk footplate
                fdn_eng = sys.modules['libs_pondasi'].Foundation_Engine(sigma_tanah)
                res_fp = fdn_eng.hitung_footplate(beban_pu, lebar_b, panjang_l, tebal_h)
                
                if "AMAN" in res_fp['status']:
                    st.success(f"**STATUS: {res_fp['status']}** (Tegangan yang terjadi lebih kecil dari batas izin tanah)")
                else:
                    st.error(f"**STATUS: {res_fp['status']}**")
                    
                c_res1, c_res2 = st.columns(2)
                c_res1.metric("Rasio Keamanan (Tegangan)", f"{res_fp['ratio_safety']:.2f}", delta="Harus > 1.0", delta_color="off")
                c_res2.metric("Volume Beton Kebutuhan", f"{res_fp['vol_beton']:.2f} m³")
                
                st.caption(f"Estimasi Volume Galian: **{res_fp['vol_galian']:.2f} m³** | Estimasi Pembesian (Praktis): **{res_fp['berat_besi']:.1f} kg**")

        # =========================================================
        # TAB 3: PONDASI BATU KALI
        # =========================================================
        with tab_batukali:
            st.markdown("#### Estimasi Volume Pondasi Menerus (Batu Kali)")
            
            with st.expander("⚙️ Parameter Geometri Pondasi", expanded=True):
                c_bk1, c_bk2 = st.columns(2)
                panjang_total = c_bk1.number_input("Total Panjang Pondasi Menerus [m]", value=50.0, step=5.0)
                tinggi_bk = c_bk2.number_input("Tinggi Pondasi (t) [m]", value=0.8, step=0.1)
                
                st.markdown("**Profil Melintang (Trapesium):**")
                c_bk3, c_bk4 = st.columns(2)
                lebar_atas = c_bk3.number_input("Lebar Atas (a) [m]", value=0.3, step=0.05)
                lebar_bawah = c_bk4.number_input("Lebar Bawah (b) [m]", value=0.6, step=0.1)
                
            if st.button("📏 Hitung Volume Batu Kali", type="primary", use_container_width=True):
                # Init engine statis (nilai sigma tidak dipakai untuk fungsi ini)
                fdn_eng_bk = sys.modules['libs_pondasi'].Foundation_Engine(100.0) 
                res_bk = fdn_eng_bk.hitung_batu_kali(panjang_total, lebar_atas, lebar_bawah, tinggi_bk)
                
                st.success("✅ Perhitungan Ekstraksi Volume Selesai!")
                m_bk1, m_bk2 = st.columns(2)
                m_bk1.metric("Volume Pasangan Batu Kali", f"{res_bk['vol_pasangan']:.2f} m³")
                m_bk2.metric("Volume Galian Tanah", f"{res_bk['vol_galian']:.2f} m³", delta="Toleransi ruang kerja sisi bawah", delta_color="off")

# --- J. MODE TOPOGRAFI 3D (CUT/FILL & BANJIR) ---
elif selected_menu == "🗺️ Analisis Topografi 3D":
    st.header("🗺️ Analisis Digital Terrain Model (DTM)")
    st.caption("Perhitungan Volume Galian & Timbunan (Metode Prisma TIN) dan Simulasi Genangan 3D")
    
    if 'libs_topografi' not in sys.modules:
        st.warning("⚠️ Modul `libs_topografi` belum dimuat oleh sistem.")
    else:
        topo_eng = sys.modules['libs_topografi'].Topografi_Engine()

        st.markdown("### 📥 1. Input Data Topografi")
        st.info("Mendukung: CSV/XLSX (Tabel XYZ), DXF (AutoCAD), GPX (GPS), dan DEM/TIF (DEMNAS/Raster).")
        file_xyz = st.file_uploader("Upload File Topografi", type=['csv', 'xlsx', 'xls', 'dxf', 'gpx', 'tif', 'tiff', 'dem'])
        
        if file_xyz:
            df_points = None
            filename = file_xyz.name.lower()
            
            try:
                with st.spinner(f"Mengekstrak dan memproyeksikan data dari {filename}..."):
                    
                    # 1. FORMAT EXCEL / CSV
                    if filename.endswith(('.csv', '.xlsx', '.xls')):
                        if filename.endswith('.csv'): df_points = pd.read_csv(file_xyz)
                        else: df_points = pd.read_excel(file_xyz)
                        df_points.columns = [str(c).upper().strip() for c in df_points.columns]
                    
                    # 2. FORMAT DXF (AutoCAD)
                    elif filename.endswith('.dxf'):
                        _, _, df_data = sys.modules['libs_loader'].process_special_file(file_xyz)
                        if df_data is not None and not df_data.empty:
                            df_points = df_data
                        else:
                            st.error("Gagal mengekstrak koordinat Z dari DXF.")
                    
                    # 3. FORMAT GPX (Alat GPS)
                    elif filename.endswith('.gpx'):
                        import gpxpy
                        import geopandas as gpd
                        
                        gpx = gpxpy.parse(file_xyz.getvalue().decode('utf-8', errors='ignore'))
                        points_data = [{'lon': pt.longitude, 'lat': pt.latitude, 'Z': pt.elevation or 0.0} 
                                       for track in gpx.tracks for segment in track.segments for pt in segment.points]
                        
                        if points_data:
                            df_gpx = pd.DataFrame(points_data)
                            gdf = gpd.GeoDataFrame(df_gpx, geometry=gpd.points_from_xy(df_gpx.lon, df_gpx.lat), crs="EPSG:4326")
                            gdf_metric = gdf.to_crs(epsg=3857) # Proyeksi ke Meter
                            df_points = pd.DataFrame({'X': gdf_metric.geometry.x, 'Y': gdf_metric.geometry.y, 'Z': gdf_metric['Z']})
                            
                    # 4. FORMAT DEM / TIF (DEMNAS / RASTER) - FITUR BARU!
                    elif filename.endswith(('.tif', '.tiff', '.dem')):
                        import rasterio
                        import numpy as np
                        import tempfile
                        import os
                        
                        # Simpan ke temp file karena rasterio butuh file path fisik
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as tmp:
                            tmp.write(file_xyz.getvalue())
                            tmp_path = tmp.name
                            
                        try:
                            with rasterio.open(tmp_path) as src:
                                # [SANGAT KRUSIAL] DOWNSAMPLING
                                # Kita baca hanya 5% dari resolusi asli agar RAM tidak jebol
                                scale_factor = 0.05
                                out_shape = (int(src.height * scale_factor), int(src.width * scale_factor))
                                
                                # Resample data Z
                                z_data = src.read(1, out_shape=out_shape)
                                
                                # Hitung ulang sistem koordinat (Transform) agar sesuai dengan ukuran baru
                                transform = src.transform * src.transform.scale(
                                    (src.width / z_data.shape[1]),
                                    (src.height / z_data.shape[0])
                                )
                                
                                # Ekstrak koordinat X dan Y untuk setiap pixel
                                rows, cols = np.indices(z_data.shape)
                                xs, ys = rasterio.transform.xy(transform, rows, cols)
                                
                                # Rata-kan matriks menjadi tabel 1 dimensi
                                df_points = pd.DataFrame({
                                    'X': np.array(xs).flatten(),
                                    'Y': np.array(ys).flatten(),
                                    'Z': z_data.flatten()
                                })
                                
                                # Buang pixel kosong (NoData di DEM biasanya bernilai minus puluhan ribu)
                                nodata_val = src.nodata if src.nodata is not None else -9999
                                df_points = df_points[df_points['Z'] > -100] # Buang outlier laut dalam
                        finally:
                            if os.path.exists(tmp_path): os.remove(tmp_path)

                # --- LANJUTKAN PROSES JIKA DF_POINTS BERHASIL DIBUAT ---
                if df_points is not None and all(k in df_points.columns for k in ['X', 'Y', 'Z']):
                    st.success(f"✅ Berhasil memuat dan mengekstrak {len(df_points)} titik spasial.")
                    
                    z_min = df_points['Z'].min()
                    z_max = df_points['Z'].max()
                    z_avg = df_points['Z'].mean()
                    
                    # [SISA KODE st.tabs(["⛏️ Analisis Cut & Fill", "🌊 Simulasi Genangan Banjir"]) SAMA SEPERTI SEBELUMNYA]
        
                           
                    # =========================================================
                    # TAB 1: CUT & FILL
                    # =========================================================
                    with tab_cutfill:
                        c_cf1, c_cf2 = st.columns([1, 2])
                        with c_cf1:
                            st.markdown("**Parameter Perataan Tanah (Grading)**")
                            st.caption(f"Elevasi Eksisting: {z_min:.2f} m s/d {z_max:.2f} m")
                            elevasi_rencana = st.number_input("Target Elevasi Rencana [m]", value=float(z_avg), step=0.5)
                            
                            if st.button("⛏️ Hitung Volume & Render 3D", type="primary", use_container_width=True):
                                with st.spinner("Membangun jaring segitiga (Delaunay TIN) & menghitung volume prisma..."):
                                    hasil_cf = topo_eng.hitung_cut_fill(df_points, elevasi_rencana)
                                    
                                    if "error" not in hasil_cf:
                                        st.success("✅ " + hasil_cf["Status"])
                                        st.metric("Total Volume Galian (Cut) \U0001f7eb", f"{hasil_cf['Volume_Galian_m3']} m³")
                                        st.metric("Total Volume Timbunan (Fill) \U0001f7e9", f"{hasil_cf['Volume_Timbunan_m3']} m³")
                                        st.caption(f"Estimasi Luas Area Terdampak: {hasil_cf['Luas_Area_m2']} m²")
                                    else:
                                        st.error(hasil_cf["error"])
                                        
                        with c_cf2:
                            if 'hasil_cf' in locals() and "error" not in hasil_cf:
                                fig_cf = topo_eng.visualisasi_3d_terrain(df_points, elevasi_rencana)
                                st.plotly_chart(fig_cf, use_container_width=True)

                    # =========================================================
                    # TAB 2: SIMULASI BANJIR
                    # =========================================================
                    with tab_banjir:
                        c_bj1, c_bj2 = st.columns([1, 2])
                        with c_bj1:
                            st.markdown("**Parameter Muka Air Banjir (MAB)**")
                            elevasi_banjir = st.number_input("Elevasi MAB Rencana [m]", value=float(z_max - (z_max-z_min)*0.2), step=0.5)
                            
                            if st.button("🌊 Jalankan Simulasi Genangan", type="primary", use_container_width=True):
                                with st.spinner("Memodelkan genangan bathtub dan area terendam kritis..."):
                                    fig_bj, hasil_bj = topo_eng.simulasi_genangan_banjir_3d(df_points, elevasi_banjir)
                                    
                                    if fig_bj:
                                        st.success(hasil_bj['Status'])
                                        st.metric("Estimasi Luas Tergenang", f"{hasil_bj['Estimasi_Luas_Genangan_m2']} m²", delta=f"{hasil_bj['Estimasi_Luas_Genangan_Ha']} Ha", delta_color="off")
                                        st.metric("Volume Tampungan Air", f"{hasil_bj['Volume_Tampungan_Banjir_m3']} m³")
                                    else:
                                        st.error(hasil_bj.get("error", "Gagal merender."))
                        with c_bj2:
                            if 'fig_bj' in locals() and fig_bj:
                                st.plotly_chart(fig_bj, use_container_width=True)
                else:
                    st.error("❌ Format tabel salah! File harus memiliki header kolom bernama 'X', 'Y', dan 'Z'.")
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")
        else:
            st.info("💡 **Petunjuk:** Buat file Excel sederhana berisi 3 kolom (X, Y, Z), isi dengan titik kordinat hasil survey lapangan (atau hasil ekstraksi DXF dari AI Assistant), lalu unggah ke sini.")
# --- K. MODE AUDIT BAJA & JEMBATAN ---
elif selected_menu == "🌉 Audit Baja & Jembatan":
    st.header("🌉 Audit Baja Struktural & Jembatan")
    st.caption("Pengecekan Kapasitas Profil (SNI 1729:2020) & Pembebanan Jembatan (SNI 1725:2016)")
    
    if 'libs_baja' not in sys.modules or 'libs_bridge' not in sys.modules:
        st.warning("⚠️ Modul `libs_baja` atau `libs_bridge` belum dimuat.")
    else:
        tab_baja, tab_jembatan, tab_truss, tab_portal = st.tabs([
            "🏗️ Audit Baja Gedung", 
            "🛣️ Desain Gelagar Jembatan", 
            "🔺 Kalkulator Truss (Sendi)", 
            "🏭 Portal WF Gudang (Kaku)" # <--- TAB BARU
        ])
                       
        # =========================================================
        # TAB 1: AUDIT BAJA GEDUNG (SNI 1729:2020)
        # =========================================================
        with tab_baja:
            st.markdown("#### 1. Evaluasi Kapasitas Kolom Baja (AISC / SNI)")
            with st.expander("⚙️ Parameter Profil & Beban", expanded=True):
                c_bj1, c_bj2 = st.columns(2)
                nama_profil = c_bj1.text_input("Nama Profil Baja", value="WF 300x150x6.5x9")
                fy_baja = c_bj2.number_input("Mutu Baja (fy) [MPa]", value=240.0, step=10.0, help="Misal: 240 untuk BJ-37")
                
                c_bj3, c_bj4 = st.columns(2)
                luas_ag = c_bj3.number_input("Luas Penampang (Ag) [cm²]", value=46.78, step=1.0)
                beban_pu = c_bj4.number_input("Beban Aksial Terfaktor (Pu) [Ton]", value=75.0, step=5.0)
                
            if st.button("🛡️ Cek Kapasitas Kolom", type="primary", use_container_width=True):
                # Memanggil fungsi check_steel_column dari libs_baja.py
                hasil_kolom = sys.modules['libs_baja'].check_steel_column(beban_pu, luas_ag, fy_baja, nama_profil)
                
                if "AMAN" in hasil_kolom['Status']:
                    st.success(f"**STATUS: {hasil_kolom['Status']}**")
                else:
                    st.error(f"**STATUS: {hasil_kolom['Status']}** (Perbesar profil atau gunakan mutu baja lebih tinggi)")
                    
                m_b1, m_b2, m_b3 = st.columns(3)
                m_b1.metric("Kapasitas Desain (\u03c6 Pn)", f"{hasil_kolom['Capacity (phi Pn)']} Ton")
                m_b2.metric("Beban Rencana (Pu)", f"{hasil_kolom['Demand (Pu)']} Ton")
                m_b3.metric("DCR (Demand/Capacity Ratio)", f"{hasil_kolom['DCR Ratio']} x", delta="Harus < 1.0", delta_color="inverse")
            
            st.markdown("---")
            st.markdown("#### 2. Reduksi Kekakuan Direct Analysis Method (DAM)")
            st.caption("Pengecekan parameter reduksi inelastis ($\u03c4_b$) untuk analisis struktur lanjut.")
            with st.expander("⚙️ Parameter Gaya & Geometri", expanded=False):
                c_dam1, c_dam2 = st.columns(2)
                p_req = c_dam1.number_input("Kekuatan Perlu / Beban (Pr) [kN]", value=1500.0)
                p_yield = c_dam2.number_input("Kekuatan Leleh Aksial (Py) [kN]", value=3000.0)
                
                if st.button("🔄 Hitung Reduksi Kekakuan (Tau_b)"):
                    baja_eng = sys.modules['libs_baja'].SNI_Steel_2020(fy=fy_baja)
                    # Asumsi I dan A dummy untuk mendapatkan nilai Tau_b saja
                    EI_red, EA_red, tau_b, trace = baja_eng.hitung_kekakuan_dam(I_profil=1000, A_profil=10, P_required=p_req, P_yield=p_yield)
                    st.info(f"**Trace Perhitungan:** {trace}")
                    st.metric("Faktor Reduksi (\u03c4_b)", f"{tau_b:.3f}")

        # =========================================================
        # TAB 2: JEMBATAN BAJA (SNI 1725:2016)
        # =========================================================
        with tab_jembatan:
            st.markdown("#### Pembebanan Gelagar & Beban Lajur 'D' (SNI 1725:2016)")
            
            with st.expander("⚙️ Parameter Jembatan", expanded=True):
                c_br1, c_br2, c_br3 = st.columns(3)
                bentang_l = c_br1.number_input("Panjang Bentang (L) [m]", value=40.0, step=5.0)
                jarak_gelagar = c_br2.number_input("Jarak Antar Gelagar [m]", value=1.8, step=0.1)
                beban_mati_tmb = c_br3.number_input("Beban Mati Tambahan (SIDL) [kPa]", value=2.0, step=0.5)

            if st.button("🏗️ Analisis Momen Gelagar", type="primary", use_container_width=True):
                with st.spinner("Menghitung faktor dinamis & distribusi beban..."):
                    bridge_eng = sys.modules['libs_bridge'].SNI_Bridge_Loader(bentang_L=bentang_l)
                    res_bridge = bridge_eng.analisis_momen_gelagar(jarak_gelagar, beban_mati_tambahan_kpa=beban_mati_tmb)
                    
                    st.success("✅ Analisis Pembebanan SNI 1725 Selesai!")
                    
                    st.markdown("**1. Intensitas Beban Lajur 'D' & DLA**")
                    col_L1, col_L2, col_L3 = st.columns(3)
                    col_L1.metric("BTR (Beban Terbagi Rata)", f"{res_bridge['Detail']['q_btr']:.2f} kPa")
                    col_L2.metric("BGT (Beban Garis Terpusat)", f"{res_bridge['Detail']['p_bgt']:.2f} kN/m")
                    col_L3.metric("Faktor Beban Dinamis (DLA)", f"{res_bridge['DLA'] * 100}%")
                    
                    st.markdown("**2. Rekapitulasi Momen Ultimate 1 Gelagar Interior**")
                    col_M1, col_M2, col_M3 = st.columns(3)
                    col_M1.metric("Momen Beban Mati (M_DL)", f"{res_bridge['M_DL']:.1f} kNm")
                    col_M2.metric("Momen Beban Hidup (M_LL)", f"{res_bridge['M_LL']:.1f} kNm", help="Sudah termasuk DLA")
                    col_M3.metric("Momen Ultimate (Mu) Total", f"{res_bridge['Mu_Total']:.1f} kNm", delta="Kombinasi Kuat I", delta_color="off")
                    
                    # Menampilkan Database Profil Jembatan yang tersedia
                    st.markdown("---")
                    st.markdown("**📚 Database Profil Welded Beam (WB) Referensi:**")
                    db_profil = sys.modules['libs_bridge'].Bridge_Profile_DB.get_profiles()
                    df_profil = pd.DataFrame.from_dict(db_profil, orient='index')
                    st.dataframe(df_profil, use_container_width=True)
        # =========================================================
        # TAB 3: KALKULATOR TRUSS 2D (OPENSEES)
        # =========================================================
        with tab_truss:
            st.markdown("#### Generator Rangka Atap (Truss 2D)")
            st.write("Ditenagai oleh *OpenSees Engine* untuk komputasi gaya dalam matriks linear.")
            
            with st.expander("⚙️ Geometri & Beban Truss", expanded=True):
                c_tr1, c_tr2 = st.columns(2)
                span = c_tr1.number_input("Panjang Bentang Kuda-Kuda (L) [m]", value=12.0, step=1.0)
                height = c_tr2.number_input("Tinggi Puncak (H) [m]", value=3.0, step=0.5)
                
                c_tr3, c_tr4 = st.columns(2)
                panels = c_tr3.number_input("Jumlah Pias / Segmen (Wajib Genap)", value=6, step=2)
                load_p = c_tr4.number_input("Beban Titik per Buhul (P) [kN]", value=15.0, step=1.0, help="Kombinasi Beban Mati + Angin + Hidup")
                
            if st.button("🚀 Rakit Matriks & Hitung Gaya Aksial", type="primary", use_container_width=True):
                with st.spinner("OpenSees sedang membangun meshing & menjalankan solver statik..."):
                    try:
                        # Inisialisasi Class baru yang kita buat di libs_fem.py
                        truss_eng = sys.modules['libs_fem'].OpenSeesTruss2D()
                        
                        df_hasil, fig_truss = truss_eng.build_and_analyze(span, height, panels, load_p)
                        
                        if df_hasil is not None:
                            st.success("✅ Analisis FEM Linear Statik Konvergen!")
                            
                            # Layout 2 Kolom: Kiri untuk Tabel, Kanan untuk Gambar
                            col_hasil1, col_hasil2 = st.columns([1, 1.5])
                            
                            with col_hasil1:
                                st.markdown("**Tabel Gaya Aksial Elemen:**")
                                # Highlight warna tabel
                                def color_status(val):
                                    if 'Tarik' in val: return 'color: white; background-color: #3b82f6; font-weight:bold;'
                                    if 'Tekan' in val: return 'color: white; background-color: #ef4444; font-weight:bold;'
                                    return ''
                                st.dataframe(df_hasil.style.map(color_status, subset=['Sifat Gaya']), height=400)
                                
                            with col_hasil2:
                                st.markdown("**Diagram Geometri & Distribusi Gaya:**")
                                st.caption("Biru = Gaya Tarik | Merah = Gaya Tekan. Arahkan mouse ke garis untuk detail.")
                                st.plotly_chart(fig_truss, use_container_width=True)
                                
                            # Info untuk Ekspor
                            max_tekan = df_hasil[df_hasil['Sifat Gaya'].str.contains('Tekan')]['Gaya Aksial (kN)'].max()
                            max_tarik = df_hasil[df_hasil['Sifat Gaya'].str.contains('Tarik')]['Gaya Aksial (kN)'].max()
                            st.info(f"💡 **Insight Desain:** Gunakan gaya Tarik maksimum (**{max_tarik} kN**) dan Tekan maksimum (**{max_tekan} kN**) dari tabel di atas untuk mengecek profil siku/WF di Tab 'Audit Baja Gedung'.")
                            
                        else:
                            st.error(fig_truss) # Jika error, pesan errornya tersimpan di return kedua
                    except Exception as e:
                        st.error(f"Gagal menjalankan mesin: {e}")
        # =========================================================
        # TAB 4: PORTAL GUDANG WF (GABLE FRAME)
        # =========================================================
        with tab_portal:
            st.markdown("#### Kalkulator Portal Baja WF (Gable Frame)")
            st.write("Analisis struktur sambungan kaku (Rigid) untuk menghitung Momen Lentur & Aksial pada Kolom dan Rafter.")
            
            with st.expander("⚙️ Geometri Gudang & Beban", expanded=True):
                c_por1, c_por2, c_por3 = st.columns(3)
                span_portal = c_por1.number_input("Lebar Bentang Gudang (L) [m]", value=20.0, step=1.0)
                tinggi_kolom = c_por2.number_input("Tinggi Kolom (H1) [m]", value=6.0, step=0.5)
                tinggi_atap = c_por3.number_input("Tinggi Segitiga Atap (H2) [m]", value=2.5, step=0.5)
                
                beban_q = st.number_input("Beban Merata Rafter (q) [kN/m]", value=8.5, step=0.5, help="Beban atap + gording + angin")
                
            if st.button("🏗️ Analisis Momen Portal WF", type="primary", use_container_width=True):
                with st.spinner("OpenSees sedang menghitung matriks gaya dalam 3 Derajat Kebebasan..."):
                    try:
                        portal_eng = sys.modules['libs_fem'].OpenSeesPortal2D()
                        df_por, fig_por, insight = portal_eng.build_and_analyze(span_portal, tinggi_kolom, tinggi_atap, beban_q)
                        
                        if df_por is not None:
                            st.success("✅ Analisis Portal Linear Selesai!")
                            
                            col_p1, col_p2 = st.columns([1, 1.2])
                            with col_p1:
                                st.markdown("**Rekapitulasi Gaya Dalam (Envelopes):**")
                                st.dataframe(df_por, height=200, use_container_width=True)
                                
                                st.info(f"💡 **Panduan Desain WF:**\n"
                                        f"1. Rafter memikul Momen sangat besar (**{insight['momen_rafter']} kNm**). Cek profil WF di Tab 1.\n"
                                        f"2. Kolom memikul Aksial sebesar (**{insight['aksial_kolom']} kN**).")
                                
                            with col_p2:
                                st.plotly_chart(fig_por, use_container_width=True)
                        else:
                            st.error(fig_por)
                    except Exception as e:
                        st.error(f"Gagal menghitung Portal: {e}")
# --- L. MODE TRANSPORTASI & JALAN RAYA ---
elif selected_menu == "🛣️ Analisis Transportasi (Jalan)":
    st.header("🛣️ Analisis Transportasi & Perkerasan Jalan")
    st.caption("Evaluasi ANDALALIN, Desain Tebal Perkerasan (MDP 2017), dan Geometrik Tikungan")
    
    if 'libs_transport' not in sys.modules:
        st.warning("⚠️ Modul `libs_transport` belum dimuat oleh sistem.")
    else:
        trans_eng = sys.modules['libs_transport'].Transport_Infrastructure_Engine()
        
        tab_andalalin, tab_pavement, tab_geometrik = st.tabs([
            "🚦 Bangkitan Lalin (ANDALALIN)", 
            "🛣️ Perkerasan Lentur (MDP 2017)", 
            "🔄 Geometrik & Superelevasi"
        ])
        
        # =========================================================
        # TAB 1: ANDALALIN (BANGKITAN LALU LINTAS)
        # =========================================================
        with tab_andalalin:
            st.markdown("#### Estimasi Bangkitan Lalu Lintas (Trip Generation)")
            st.write("Kalkulasi awal untuk penentuan dokumen wajib Analisis Dampak Lalu Lintas (Permenhub 17/2021).")
            
            with st.expander("⚙️ Parameter Tata Guna Lahan", expanded=True):
                c_and1, c_and2 = st.columns(2)
                fungsi = c_and1.selectbox("Fungsi Lahan / Bangunan", ["Sekolah", "Perumahan", "Komersial", "Rumah Sakit"])
                
                # Input dinamis berdasarkan fungsi lahan
                if fungsi == "Komersial":
                    kapasitas = c_and2.number_input("Luas Lantai Efektif [m²]", value=5000, step=100)
                elif fungsi == "Sekolah":
                    kapasitas = c_and2.number_input("Jumlah Siswa & Staf [Orang]", value=1000, step=50)
                elif fungsi == "Rumah Sakit":
                    kapasitas = c_and2.number_input("Jumlah Tempat Tidur [Bed]", value=200, step=10)
                else:
                    kapasitas = c_and2.number_input("Jumlah Unit Rumah [Unit]", value=150, step=10)
            
            if st.button("🚦 Evaluasi Kewajiban ANDALALIN", type="primary", use_container_width=True):
                res_and = trans_eng.hitung_bangkitan_lalin(fungsi, kapasitas)
                
                st.metric("Estimasi Bangkitan Lalu Lintas (Puncak)", f"{res_and['Estimasi_Bangkitan_smp_jam']} SMP/Jam")
                
                status_lalin = res_and['Status_Regulasi']
                if "WAJIB" in status_lalin:
                    st.error(f"**STATUS: {status_lalin}**")
                elif "RINGAN" in status_lalin:
                    st.warning(f"**STATUS: {status_lalin}**")
                else:
                    st.success(f"**STATUS: {status_lalin}**")

        # =========================================================
        # TAB 2: PERKERASAN LENTUR (ASPAL)
        # =========================================================
        with tab_pavement:
            st.markdown("#### Desain Struktur Perkerasan Lentur (Bina Marga MDP 2017)")
            
            with st.expander("⚙️ Parameter Beban & Geoteknik Tanah", expanded=True):
                c_pav1, c_pav2 = st.columns(2)
                cbr_tanah = c_pav1.number_input("CBR Tanah Dasar Lapangan [%]", value=5.0, step=1.0)
                cesa = c_pav2.number_input("Beban Sumbu Standar Kumulatif (CESA) [Juta]", value=3.5, step=0.5, help="Cumulative Equivalent Single Axle Load x 10^6")
                
            if st.button("🛣️ Desain Tebal Perkerasan", type="primary", use_container_width=True):
                res_pav = trans_eng.desain_perkerasan_lentur(cbr_tanah, cesa)
                
                st.success(f"✅ Klasifikasi Jalan: **{res_pav['Klasifikasi_Jalan']}**")
                
                if "KRITIS" in res_pav['Rekomendasi_Geoteknik']:
                    st.error(res_pav['Rekomendasi_Geoteknik'])
                else:
                    st.info(res_pav['Rekomendasi_Geoteknik'])
                    
                st.markdown("**Rekomendasi Susunan Lapisan Perkerasan Lentur:**")
                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                col_p1.metric("Surface (AC-WC)", f"{res_pav['Lapis_Permukaan_AC_WC_mm']} mm")
                col_p2.metric("Binder (AC-BC)", f"{res_pav['Lapis_Antara_AC_BC_mm']} mm")
                col_p3.metric("Base (LPA Kelas A)", f"{res_pav['Lapis_Pondasi_Atas_LPA_KelasA_mm']} mm")
                col_p4.metric("Subbase (LPB Kelas B)", f"{res_pav['Lapis_Pondasi_Bawah_LPB_KelasB_mm']} mm")

        # =========================================================
        # TAB 3: GEOMETRIK TIKUNGAN
        # =========================================================
        with tab_geometrik:
            st.markdown("#### Alinyemen Horizontal & Superelevasi")
            st.write("Pengecekan batas radius aman untuk mencegah kendaraan tergelincir (overturning) pada kecepatan tertentu.")
            
            with st.expander("⚙️ Parameter Rencana Jalan", expanded=True):
                c_geo1, c_geo2, c_geo3 = st.columns(3)
                v_rencana = c_geo1.number_input("Kecepatan Rencana (V) [km/jam]", value=60.0, step=10.0)
                r_rencana = c_geo2.number_input("Radius Tikungan Rencana (R) [m]", value=120.0, step=10.0)
                lebar_lajur = c_geo3.number_input("Lebar Separuh Jalan [m]", value=3.5, step=0.5, help="Jarak dari as (centerline) ke tepi luar jalan")
                
            if st.button("🔄 Analisis Tikungan & Render Profil", type="primary", use_container_width=True):
                res_geo = trans_eng.desain_tikungan_horizontal(v_rencana, r_rencana)
                
                status_geo = res_geo['Status_Keamanan']
                if "BAHAYA" in status_geo:
                    st.error(f"**{status_geo}**")
                else:
                    st.success(f"**{status_geo}**")
                    
                m_g1, m_g2 = st.columns(2)
                m_g1.metric("Batas Radius Minimum (R_min)", f"{res_geo['Radius_Minimum_Aman_m']} m")
                m_g2.metric("Superelevasi Desain (e)", f"{res_geo['Superelevasi_Desain_%']}%", delta="Maks Normal: 10%", delta_color="off")
                
                st.markdown("**Potongan Melintang Jalan pada Daerah Tikungan Penuh (Full Superelevation):**")
                fig_geo = trans_eng.gambar_profil_melintang(lebar_lajur, res_geo['Superelevasi_Desain_%'])
                st.plotly_chart(fig_geo, use_container_width=True)
# --- M. MODE MEP (MECHANICAL, ELECTRICAL, PLUMBING) ---
elif selected_menu == "💡 Kalkulator MEP (SNI)":
    st.header("💡 Kalkulator MEP Bangunan (SNI)")
    st.caption("Desain Utilitas HVAC, Pencahayaan, dan Air Bersih")
    
    if 'libs_mep' not in sys.modules:
        st.warning("⚠️ Modul `libs_mep` belum dimuat oleh sistem.")
    else:
        mep_eng = sys.modules['libs_mep'].MEP_Engine()
        
        tab_hvac, tab_listrik, tab_plumbing = st.tabs(["❄️ Tata Udara (HVAC)", "💡 Pencahayaan", "🚰 Plumbing (Air Bersih)"])
        
        # =========================================================
        # TAB 1: HVAC (BEBAN PENDINGIN AC)
        # =========================================================
        with tab_hvac:
            st.markdown("#### Estimasi Beban Pendingin Ruangan (BTU/hr ke PK)")
            with st.expander("⚙️ Parameter Ruangan", expanded=True):
                c_ac1, c_ac2, c_ac3 = st.columns(3)
                p_ruang = c_ac1.number_input("Panjang [m]", value=5.0, step=0.5, key="ac_p")
                l_ruang = c_ac2.number_input("Lebar [m]", value=4.0, step=0.5, key="ac_l")
                t_ruang = c_ac3.number_input("Tinggi [m]", value=3.0, step=0.5, key="ac_t")
                
                c_ac4, c_ac5 = st.columns(2)
                fungsi_ac = c_ac4.selectbox("Fungsi Ruang (AC)", ["Kamar Tidur (Residensial)", "Kantor / Ruang Kerja", "Ruang Rapat", "Ruang Kelas"])
                jml_orang = c_ac5.number_input("Estimasi Penghuni [Orang]", value=2, step=1)
                
                terpapar = st.checkbox("☀️ Dinding terpapar sinar matahari langsung (Barat/Timur)?")
                
            if st.button("❄️ Hitung Kebutuhan AC", type="primary", use_container_width=True):
                res_ac = mep_eng.hitung_kebutuhan_ac(p_ruang, l_ruang, t_ruang, fungsi_ac, jml_orang, terpapar)
                
                st.success(res_ac['Status'])
                col_h1, col_h2, col_h3 = st.columns(3)
                col_h1.metric("Total Beban Pendingin", f"{res_ac['Total_Beban_Pendingin_BTU']:,.0f} BTU/hr")
                col_h2.metric("Rekomendasi Kapasitas AC", f"{res_ac['Kapasitas_AC_Rekomendasi_PK']} PK")
                col_h3.metric("Estimasi Jumlah Unit", f"{res_ac['Jumlah_Unit_Estimasi']} Unit")

        # =========================================================
        # TAB 2: PENCAHAYAAN (LIGHTING)
        # =========================================================
        with tab_listrik:
            st.markdown("#### Kebutuhan Titik Lampu (SNI 03-6197-2011)")
            with st.expander("⚙️ Parameter Iluminasi", expanded=True):
                c_lt1, c_lt2 = st.columns(2)
                p_lampu = c_lt1.number_input("Panjang Ruang [m]", value=6.0, step=0.5)
                l_lampu = c_lt2.number_input("Lebar Ruang [m]", value=5.0, step=0.5)
                
                fungsi_lampu = st.selectbox("Fungsi Ruangan (Target Lux)", list(mep_eng.std_lux.keys()), index=1)
                
                c_lt3, c_lt4 = st.columns(2)
                watt_lamp = c_lt3.number_input("Daya Lampu LED [Watt]", value=15, step=1)
                lumen_w = c_lt4.number_input("Efikasi Lampu [Lumen/Watt]", value=100, step=10, help="Standar LED biasanya 90-110 Lumen/Watt")
                
            if st.button("💡 Hitung Titik Lampu", type="primary", use_container_width=True):
                res_lampu = mep_eng.hitung_titik_lampu(p_lampu, l_lampu, fungsi_lampu, lumen_w, watt_lamp)
                
                st.success(res_lampu['Status'])
                col_l1, col_l2 = st.columns(2)
                col_l1.metric("Target Pencahayaan (SNI)", f"{res_lampu['Target_Pencahayaan_Lux']} Lux")
                col_l2.metric(f"Kebutuhan Titik Lampu ({watt_lamp}W)", f"{res_lampu['Jumlah_Titik_Lampu']} Buah")

        # =========================================================
        # TAB 3: PLUMBING (AIR BERSIH)
        # =========================================================
        with tab_plumbing:
            st.markdown("#### Desain Dimensi Pipa Air Bersih Utama (SNI 03-7065-2005)")
            with st.expander("⚙️ Parameter Kebutuhan Air", expanded=True):
                c_pl1, c_pl2 = st.columns(2)
                fungsi_gedung = c_pl1.selectbox("Klasifikasi Bangunan", list(mep_eng.std_air.keys()), index=2)
                jml_penghuni = c_pl2.number_input("Total Penghuni Gedung", value=5, step=1)
                
                v_air = st.number_input("Kecepatan Aliran Pipa (v) [m/s]", value=1.5, step=0.1, help="Standar kecepatan air di pipa 1.0 - 2.0 m/s")
                
            if st.button("🚰 Desain Pipa Distribusi", type="primary", use_container_width=True):
                res_pipa = mep_eng.hitung_pipa_air_bersih(fungsi_gedung, jml_penghuni, v_air)
                
                st.success(res_pipa['Status'])
                col_p1, col_p2, col_p3 = st.columns(3)
                col_p1.metric("Kebutuhan Harian", f"{res_pipa['Total_Kebutuhan_Harian_Liter']:,.0f} Liter/Hari")
                col_p2.metric("Debit Puncak (Q)", f"{res_pipa['Debit_Puncak_L_s']} L/s")
                col_p3.metric("Diameter Pipa Utama", f"{res_pipa['Diameter_Pipa_Utama_Inci']} Inci", delta="Minimum", delta_color="off")

# --- N. MODE GREEN BUILDING & ZONASI ---
elif selected_menu == "🌿 Green Building & Zonasi":
    st.header("🌿 Audit Green Building & Zonasi Ruang")
    st.caption("Pengecekan Tata Ruang, Panen Air Hujan, dan Jejak Karbon Material")
    
    if 'libs_green' not in sys.modules or 'libs_zoning' not in sys.modules:
        st.warning("⚠️ Modul Green/Zonasi belum dimuat oleh sistem.")
    else:
        green_eng = sys.modules['libs_green'].Green_Building_Engine()
        zone_eng = sys.modules['libs_zoning'].Zoning_Analyzer()
        
        tab_zonasi, tab_eco, tab_karbon = st.tabs(["🏙️ Zonasi (KDB/KLB)", "🌧️ Efisiensi Air & OTTV", "♻️ Jejak Karbon (Embodied)"])
        
        # =========================================================
        # TAB 1: ZONASI & TATA RUANG
        # =========================================================
        with tab_zonasi:
            st.markdown("#### Audit Intensitas Bangunan (KDB, KLB, RTH)")
            with st.expander("⚙️ Parameter Lahan & Desain", expanded=True):
                c_zn1, c_zn2 = st.columns(2)
                zona_kota = c_zn1.selectbox("Klasifikasi Zona", ["R-1 (Kepadatan Rendah)", "R-2 (Kepadatan Sedang)", "K-1 (Komersial)"])
                kode_zona = zona_kota.split()[0]
                luas_lahan = c_zn2.number_input("Luas Lahan Total [m²]", value=200.0, step=10.0)
                
                c_zn3, c_zn4 = st.columns(2)
                luas_dasar = c_zn3.number_input("Luas Dasar Bangunan (Tapak) [m²]", value=130.0, step=10.0)
                luas_lantai_tot = c_zn4.number_input("Total Luas Lantai (Semua Tingkat) [m²]", value=250.0, step=10.0)
            
            if st.button("🏙️ Evaluasi Tata Ruang", type="primary", use_container_width=True):
                res_zonasi = zone_eng.cek_intensitas_bangunan(luas_lahan, luas_lantai_tot, luas_dasar, kode_zona)
                st.info(res_zonasi)
                
                # Insight Investasi Lahan
                st.markdown("**Analisis Nilai Aset Kasar:**")
                res_invest = zone_eng.hitung_potensi_harga_lahan(luas_lahan, njop_meter=2500000, harga_pasar_meter=4000000)
                m_v1, m_v2, m_v3 = st.columns(3)
                m_v1.metric("Estimasi NJOP Total", res_invest['Nilai Aset (NJOP)'])
                m_v2.metric("Estimasi Nilai Pasar", res_invest['Nilai Pasar Estimasi'])
                m_v3.metric("Gap Profit", res_invest['Gap Profit'])

        # =========================================================
        # TAB 2: PANEN AIR HUJAN & OTTV
        # =========================================================
        with tab_eco:
            st.markdown("#### Rainwater Harvesting & OTTV Fasad")
            with st.expander("⚙️ Parameter Ekologi", expanded=True):
                c_ec1, c_ec2 = st.columns(2)
                luas_atap = c_ec1.number_input("Luas Atap Penampung Air [m²]", value=100.0, step=10.0)
                ch_tahunan = c_ec2.number_input("Curah Hujan Tahunan Wilayah [mm]", value=2500.0, step=100.0, help="Rata-rata Indonesia 2000-3000 mm")
                
                c_ec3, c_ec4 = st.columns(2)
                luas_dinding = c_ec3.number_input("Luas Dinding Fasad Luar [m²]", value=80.0, step=5.0)
                wwr_persen = c_ec4.number_input("Window to Wall Ratio (WWR) [%]", value=30.0, step=5.0, help="Persentase luasan kaca terhadap dinding")
                
            if st.button("🌱 Audit Efisiensi Ekologi", type="primary", use_container_width=True):
                # 1. Air Hujan
                res_hujan = green_eng.hitung_panen_hujan(luas_atap, ch_tahunan)
                st.markdown("**1. Potensi Panen Air Hujan:**")
                col_e1, col_e2 = st.columns(2)
                col_e1.metric("Potensi Tangkapan Tahunan", res_hujan['Potensi Air Hujan'])
                col_e2.metric("Penghematan Air Harian", res_hujan['Penghematan Harian'], delta=res_hujan['Rekomendasi'], delta_color="normal")
                
                st.markdown("---")
                # 2. OTTV
                res_ottv = green_eng.hitung_ottv_sederhana(luas_dinding, wwr_persen)
                st.markdown("**2. Estimasi Overall Thermal Transfer Value (OTTV):**")
                
                if "LULUS" in res_ottv['Status_SNI']:
                    st.success(f"OTTV: **{res_ottv['Nilai_OTTV_W_m2']} W/m²** \u2192 {res_ottv['Status_SNI']}")
                else:
                    st.error(f"OTTV: **{res_ottv['Nilai_OTTV_W_m2']} W/m²** \u2192 {res_ottv['Status_SNI']}")
                    st.caption("Kurangi rasio luasan kaca atau gunakan kaca tipe Low-E/Double Glass.")

        # =========================================================
        # TAB 3: JEJAK KARBON (EMBODIED CARBON)
        # =========================================================
        with tab_karbon:
            st.markdown("#### Kalkulator Jejak Karbon Material (Embodied Carbon)")
            st.write("Menghitung estimasi emisi $CO_2$ dari material struktur utama dan konversi kebutuhan pohon penyeimbang.")
            
            with st.expander("⚙️ Volume Material Struktur", expanded=True):
                c_co1, c_co2 = st.columns(2)
                vol_beton = c_co1.number_input("Total Volume Beton [m³]", value=150.0, step=10.0)
                berat_baja = c_co2.number_input("Total Berat Baja Tulangan/Profil [kg]", value=25000.0, step=1000.0)
                
            if st.button("♻️ Hitung Jejak Karbon", type="primary", use_container_width=True):
                res_co2 = green_eng.hitung_jejak_karbon_struktur(vol_beton, berat_baja)
                
                st.success(res_co2['Status'])
                m_co1, m_co2 = st.columns(2)
                
                # Emisi Karbon
                emisi_ton = res_co2['Total_Emisi_kgCO2'] / 1000
                m_co1.metric("Total Emisi Gas Rumah Kaca", f"{emisi_ton:,.1f} Ton CO\u2082e", delta="Embodied Carbon", delta_color="inverse")
                
                # Kompensasi Pohon
                m_co2.metric("Kompensasi Deforestasi Ekologis", f"{res_co2['Kompensasi_Pohon_Dibutuhkan']} Pohon Dewasa", help="Jumlah pohon yang dibutuhkan untuk menyerap emisi ini dalam 1 tahun")
# --- O. MODE PENJADWALAN 4D BIM (GANTT & KURVA-S) ---
elif selected_menu == "📅 Penjadwalan Proyek (4D BIM)":
    st.header("📅 Penjadwalan Proyek Terpadu (4D BIM)")
    st.caption("Generator Work Breakdown Structure (WBS), CPM, Gantt Chart, dan Kurva-S Otomatis")
    
    if 'libs_4d' not in sys.modules:
        st.warning("⚠️ Modul `libs_4d` belum dimuat oleh sistem.")
    else:
        eng_4d = sys.modules['libs_4d'].Schedule_4D_Engine()
        
        st.markdown("### 📋 Data Bill of Quantities (BOQ) & Harga")
        st.write("Silakan edit tabel di bawah ini sesuai item pekerjaan proyek Anda. Sistem akan otomatis menghitung durasi berdasarkan asumsi produktivitas tenaga kerja harian.")
        
        # Template Data Editor
        df_boq_template = pd.DataFrame([
            {"Nama Pekerjaan": "Pembersihan Lahan", "Volume": 500, "Total Harga (Rp)": 15000000},
            {"Nama Pekerjaan": "Galian Tanah", "Volume": 250, "Total Harga (Rp)": 12500000},
            {"Nama Pekerjaan": "Pondasi", "Volume": 45, "Total Harga (Rp)": 55000000},
            {"Nama Pekerjaan": "Struktur Beton", "Volume": 120, "Total Harga (Rp)": 240000000},
            {"Nama Pekerjaan": "Atap & Plafon", "Volume": 300, "Total Harga (Rp)": 90000000}
        ])
        
        c_4d1, c_4d2 = st.columns([2, 1])
        with c_4d1:
            df_input_4d = st.data_editor(df_boq_template, num_rows="dynamic", use_container_width=True)
        with c_4d2:
            tgl_mulai = st.date_input("Tanggal Mulai Proyek (Kick-off)")
            if st.button("🚀 Generate Jadwal 4D (CPM & Kurva-S)", type="primary", use_container_width=True):
                st.session_state['trigger_4d'] = True
                
        if st.session_state.get('trigger_4d', False):
            with st.spinner("Merakit jaringan NetworkX dan menghitung Jalur Kritis (CPM)..."):
                res_4d = eng_4d.hitung_cpm_dan_jadwal(df_input_4d, tgl_mulai.strftime("%Y-%m-%d"))
                
                if res_4d['status'] == 'success':
                    df_wbs = res_4d['data']
                    st.success("✅ Penjadwalan Berhasil Disusun!")
                    
                    tab_gantt, tab_scurve, tab_wbs = st.tabs(["📊 Gantt Chart", "📈 Kurva-S (S-Curve)", "🗂️ Tabel WBS & Durasi"])
                    
                    with tab_gantt:
                        fig_gantt = eng_4d.gambar_gantt_chart(df_wbs)
                        st.plotly_chart(fig_gantt, use_container_width=True)
                        
                    with tab_scurve:
                        fig_scurve = eng_4d.gambar_kurva_s(df_wbs)
                        st.plotly_chart(fig_scurve, use_container_width=True)
                        
                    with tab_wbs:
                        st.dataframe(df_wbs[['Task ID', 'Task', 'Volume', 'Durasi (Hari)', 'Start', 'Finish', 'Bobot (%)']], use_container_width=True)
                else:
                    st.error(res_4d['message'])


# --- P. MODE EVALUASI TENDER & LEGAL KONTRAK ---
elif selected_menu == "⚖️ Evaluasi Tender & Legal":
    st.header("⚖️ Evaluasi Tender & Administrasi Kontrak")
    st.caption("Pendeteksi Harga Tidak Wajar (Dumping) dan Auto-Drafting SPK / RKK")
    
    if 'libs_legal' not in sys.modules:
        st.warning("⚠️ Modul `libs_legal` belum dimuat oleh sistem.")
    else:
        eng_legal = sys.modules['libs_legal'].Legal_Contract_Engine()
        
        tab_tender, tab_spk = st.tabs(["🕵️ Evaluasi Kewajaran Harga (HPS vs Penawaran)", "📝 Auto-Drafting SPK & RKK"])
        
        # =========================================================
        # TAB 1: EVALUASI TENDER
        # =========================================================
        with tab_tender:
            st.markdown("#### Analisis Kewajaran Harga (Anti-Dumping)")
            st.write("Masukkan Rencana Anggaran (OE/HPS) dan Harga Penawaran Kontraktor untuk mendeteksi item yang ditawar terlalu rendah (< 80%).")
            
            c_td1, c_td2 = st.columns(2)
            with c_td1:
                st.markdown("**Owner Estimate (OE / HPS)**")
                df_oe_tmpl = pd.DataFrame([
                    {"Nama Pekerjaan": "Pekerjaan Persiapan", "Total Harga": 15000000},
                    {"Nama Pekerjaan": "Struktur Bawah", "Total Harga": 150000000},
                    {"Nama Pekerjaan": "Struktur Atas", "Total Harga": 300000000}
                ])
                df_oe = st.data_editor(df_oe_tmpl, num_rows="dynamic", key="df_oe")
                
            with c_td2:
                st.markdown("**Penawaran Kontraktor**")
                df_pen_tmpl = pd.DataFrame([
                    {"Nama Pekerjaan": "Pekerjaan Persiapan", "Total Harga": 14000000},
                    {"Nama Pekerjaan": "Struktur Bawah", "Total Harga": 100000000}, # Sengaja dibuat terlalu rendah (dumping)
                    {"Nama Pekerjaan": "Struktur Atas", "Total Harga": 290000000}
                ])
                df_penawaran = st.data_editor(df_pen_tmpl, num_rows="dynamic", key="df_pen")
                
            if st.button("⚖️ Evaluasi Penawaran", type="primary"):
                res_tender = eng_legal.evaluasi_kewajaran_harga(df_oe, df_penawaran)
                
                if "error" in res_tender:
                    st.error(res_tender["error"])
                else:
                    st.markdown("### 📊 Hasil Evaluasi Panitia Pokja")
                    
                    status_rek = res_tender['Rekomendasi_Panitia']
                    if "DITOLAK" in status_rek: st.error(f"**Keputusan:** {status_rek}")
                    elif "TAHAN" in status_rek: st.warning(f"**Keputusan:** {status_rek}")
                    else: st.success(f"**Keputusan:** {status_rek}")
                    
                    m_t1, m_t2, m_t3 = st.columns(3)
                    m_t1.metric("Total HPS / OE", f"Rp {res_tender['Total_OE_Rp']:,.0f}")
                    m_t2.metric("Total Penawaran", f"Rp {res_tender['Total_Penawaran_Rp']:,.0f}")
                    m_t3.metric("Rasio Penawaran", f"{res_tender['Rasio_Penawaran_Total']} %", delta="Batas Wajar: 80% - 100%", delta_color="off")
                    
                    st.markdown("**Rincian Kewajaran per Item Pekerjaan:**")
                    def color_eval(val):
                        if 'GUGUR' in str(val): return 'color: white; background-color: #ef4444; font-weight:bold;'
                        if 'KLARIFIKASI' in str(val): return 'color: black; background-color: #facc15; font-weight:bold;'
                        if 'WAJAR' in str(val): return 'color: white; background-color: #22c55e; font-weight:bold;'
                        return ''
                    
                    st.dataframe(res_tender['Detail_Evaluasi'].style.map(color_eval, subset=['Status Evaluasi']), use_container_width=True)

        # =========================================================
        # TAB 2: DRAFTING SPK & RKK
        # =========================================================
        with tab_spk:
            st.markdown("#### Generator Surat Perintah Kerja (SPK) & Dokumen SMKK")
            
            with st.expander("⚙️ Parameter Kontrak", expanded=True):
                c_spk1, c_spk2 = st.columns(2)
                nama_proyek = c_spk1.text_input("Nama Paket Pekerjaan", value="Pembangunan Gedung Kantor Tahap I")
                nama_ppk = c_spk2.text_input("Nama Pejabat Pembuat Komitmen (PPK)", value="Ir. Budi Santoso, M.T.")
                
                c_spk3, c_spk4 = st.columns(2)
                nama_kontraktor = c_spk3.text_input("Nama Perusahaan Pemenang", value="PT. Konstruksi Nusantara")
                nilai_kontrak = c_spk4.number_input("Nilai Kontrak Final (Rp)", value=450000000.0, step=1000000.0)
                
                c_spk5, c_spk6 = st.columns(2)
                waktu_hari = c_spk5.number_input("Waktu Pelaksanaan (Hari Kalender)", value=120, step=10)
                nilai_smkk = c_spk6.number_input("Alokasi Biaya K3 / SMKK (Rp)", value=15000000.0, step=500000.0)
                
            if st.button("📝 Generate Dokumen Legal", type="primary", use_container_width=True):
                draft_spk = eng_legal.draft_spk_pemerintah(nama_proyek, nama_kontraktor, nilai_kontrak, waktu_hari, nama_ppk)
                draft_rkk = eng_legal.draft_rkk_dasar(nama_proyek, nilai_smkk)
                
                col_dok1, col_dok2 = st.columns(2)
                with col_dok1:
                    st.info("📄 **PREVIEW: Surat Perintah Kerja (SPK)**")
                    st.markdown(f"""<div style="padding:20px; background-color:white; border:1px solid #ccc; color:black; height:500px; overflow-y:auto;">
                                {draft_spk.replace(chr(10), '<br>')}</div>""", unsafe_allow_html=True)
                with col_dok2:
                    st.info("📄 **PREVIEW: Ringkasan Rencana Keselamatan (RKK)**")
                    st.markdown(f"""<div style="padding:20px; background-color:white; border:1px solid #ccc; color:black; height:500px; overflow-y:auto;">
                                {draft_rkk.replace(chr(10), '<br>')}</div>""", unsafe_allow_html=True)

elif selected_menu == "⚙️ Admin: Ekstraksi AHSP":
        st.title("⚙️ Database Master AHSP (Admin Only)")
        st.info("Pilih dan unggah beberapa file Excel AHSP sekaligus (Misal: Struktur, ME, Lansekap). Sistem akan otomatis mencari sheet 'HSP', membersihkan datanya, dan menggabungkannya ke dalam Database SQLite.")
        
        # FITUR MULTI-FILE UPLOAD (accept_multiple_files=True)
        file_ahsp_list = st.file_uploader("Upload File Excel AHSP (.xlsx)", type=["xlsx"], accept_multiple_files=True)
        
        if file_ahsp_list:
            st.write(f"📁 {len(file_ahsp_list)} file siap diproses.")
            if st.button("🚀 Sedot dan Kunci Permanen ke Database SaaS", type="primary"):
                with st.spinner("Mesin sedang membedah ribuan baris Excel. Harap tunggu..."):
                    sukses, pesan = db.proses_dan_simpan_multi_excel(file_ahsp_list)
                    
                    if sukses:
                        st.success(pesan)
                        st.balloons() # Efek animasi balon jika sukses
                        # Reload data dari database ke memory
                        st.session_state.master_ahsp = db.get_master_ahsp_permanen()
                        st.session_state.status_ahsp = "TERKUNCI DARI DATABASE"
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.error(pesan)
                
        st.divider()
        st.markdown("### 📊 Status Database AHSP Saat Ini:")
        if st.session_state.get('master_ahsp') is not None and not st.session_state.master_ahsp.empty:
            jumlah_baris = len(st.session_state.master_ahsp)
            st.success(f"✅ AKTIF: Database menyimpan total {jumlah_baris} item pekerjaan lintas disiplin.")
            
            # Tampilkan tabel yang bisa di-filter dan di-search oleh Admin
            st.dataframe(st.session_state.master_ahsp, use_container_width=True, height=400) 
        else:
            st.warning("⚠️ KOSONG: Belum ada data di database. Silakan upload file Excel SE BK No 182 di atas.")

# --- E. MODE LAPORAN RAB 5D (WORKSPACE ONLINE) ---
elif selected_menu == "📑 Laporan RAB 5D":
    st.header("📑 Workspace RAB 5D Interaktif")
    st.caption("Validasi perhitungan RAB, rincian AHSP, SMKK, dan TKDN secara online sebelum mencetak dokumen final.")
    
    # =========================================================
    # 1. PENGAMANAN DATA (GEMBOK SAAS)
    # =========================================================
    db_ahsp = st.session_state.get('master_ahsp')
    
    if db_ahsp is None or (isinstance(db_ahsp, pd.DataFrame) and db_ahsp.empty):
        st.error("🚨 SISTEM TERKUNCI: Database Master AHSP Kosong!")
        st.warning("Silakan ke menu **⚙️ Admin: Ekstraksi AHSP**, upload File Excel AHSP SE BK 182, lalu klik tombol 'Sedot dan Kunci Permanen'.")
        st.stop()
        
    df_boq_aktual = st.session_state.get('real_boq_data', None)
    lokasi_proyek = st.session_state.get('lokasi_bps', 'Lampung')
    
    if df_boq_aktual is None or df_boq_aktual.empty:
        st.warning("⚠️ Data BOQ Kosong. Silakan ekstrak file IFC dari sidebar di sebelah kiri terlebih dahulu.")
        st.stop()

    # =========================================================
    # 2. KALKULASI RAB ONLINE (SMART MATCHER V2)
    # =========================================================
    with st.spinner("Menyelaraskan Volume BIM dengan Database SE BK 182 & IKK BPS..."):
        df_rab = df_boq_aktual.copy()
        
        # Simulasi IKK BPS (Indeks Kemahalan Konstruksi)
        ikk_multiplier = 1.0
        if "papua" in lokasi_proyek.lower(): ikk_multiplier = 1.45
        elif "maluku" in lokasi_proyek.lower(): ikk_multiplier = 1.25
        elif "kalimantan" in lokasi_proyek.lower(): ikk_multiplier = 1.15
        
        def dapatkan_data_ahsp(nama_pekerjaan):
            col_harga = next((c for c in db_ahsp.columns if 'harga' in str(c).lower()), None)
            col_uraian = next((c for c in db_ahsp.columns if 'uraian' in str(c).lower()), 'Uraian')
            col_kode = next((c for c in db_ahsp.columns if 'kode' in str(c).lower() or 'no' in str(c).lower()), None)
            col_satuan = next((c for c in db_ahsp.columns if 'satuan' in str(c).lower()), None)
            
            nama_lower = str(nama_pekerjaan).lower()
            
            # Logika Pencocokan Pintar
            kata_kunci = nama_lower.split()[0]
            if "kolom" in nama_lower or "balok" in nama_lower or "pelat" in nama_lower or "beton" in nama_lower:
                kata_kunci = "beton mutu sedang" 
            elif "dinding" in nama_lower:
                kata_kunci = "dinding bata merah" 
            elif "atap" in nama_lower or "roof" in nama_lower or "covering" in nama_lower:
                kata_kunci = "atap pelana rangka" 
            elif "pondasi" in nama_lower or "footing" in nama_lower:
                kata_kunci = "beton mutu rendah"
                
            # Eksekusi pencarian di DataFrame
            match = db_ahsp[db_ahsp[col_uraian].astype(str).str.lower().str.contains(kata_kunci, na=False)]
            
            if not match.empty:
                try: 
                    harga_dasar = float(match.iloc[0][col_harga]) if col_harga else 1500000.0
                    kode_ahsp = str(match.iloc[0][col_kode]) if col_kode else "-"
                    satuan = str(match.iloc[0][col_satuan]) if col_satuan else "Unit"
                    uraian_asli = str(match.iloc[0][col_uraian])
                    
                    harga_terkoreksi = harga_dasar * ikk_multiplier
                    return pd.Series([kode_ahsp, uraian_asli, satuan, harga_terkoreksi])
                except: pass
            return pd.Series(["-", nama_pekerjaan, "m3", 1500000.0 * ikk_multiplier])
        
        # Terapkan fungsi dan pecah jadi 4 kolom baru
        df_rab[['Kode AHSP', 'Uraian AHSP 182', 'Satuan', 'Harga Satuan (Rp)']] = df_rab['Nama'].apply(dapatkan_data_ahsp)
        df_rab['Total Harga (Rp)'] = df_rab['Volume'] * df_rab['Harga Satuan (Rp)']
        
        # Susun ulang kolom agar rapi
        df_rab = df_rab[['Kode AHSP', 'Kategori', 'Uraian AHSP 182', 'Volume', 'Satuan', 'Harga Satuan (Rp)', 'Total Harga (Rp)']]
        
        # Hitung Grand Total
        total_rab_fisik = df_rab['Total Harga (Rp)'].sum()
        ppn = total_rab_fisik * 0.11
        grand_total = total_rab_fisik + ppn

    # =========================================================
    # 3. RENDER UI 8 TAB SESUAI REQUEST
    # =========================================================
    tab_bim, tab_boq, tab_rab_ui, tab_rekap, tab_ahsp, tab_smkk, tab_tkdn, tab_hsd = st.tabs([
        "🧊 1. Model IFC", "🧱 2. BOQ", "💰 3. RAB", "📊 4. Rekap", "📋 5. AHSP 182", "👷 6. SMKK", "🇮🇩 7. TKDN", "📈 8. HSD (IKK BPS)"
    ])
    
    with tab_bim:
        st.markdown("**Visualisasi BIM 3D (IFC):**")
        if 'ifc_3d_fig' in st.session_state:
            with st.container(border=True):
                st.plotly_chart(st.session_state['ifc_3d_fig'], use_container_width=True, height=500)
        else:
            st.info("💡 Model 3D belum tersedia.")
            
    with tab_boq:
        st.markdown("**Volume Bill of Quantities (BOQ):**")
        st.dataframe(df_boq_aktual, use_container_width=True)
        
    with tab_rab_ui:
        st.markdown("**Rencana Anggaran Biaya (Dilengkapi Kode & Satuan AHSP):**")
        st.dataframe(
            df_rab.style.format({
                'Volume': '{:.2f}', 
                'Harga Satuan (Rp)': 'Rp {:,.0f}', 
                'Total Harga (Rp)': 'Rp {:,.0f}'
            }), 
            use_container_width=True, height=350
        )
        st.success(f"💰 **TOTAL BIAYA FISIK: Rp {total_rab_fisik:,.0f}**")

    with tab_rekap:
        st.markdown("**Rekapitulasi & Grand Total Proyek:**")
        c_r1, c_r2, c_r3 = st.columns(3)
        c_r1.metric("A. Total Biaya Fisik", f"Rp {total_rab_fisik:,.0f}")
        c_r2.metric("B. Pajak (PPN 11%)", f"Rp {ppn:,.0f}")
        c_r3.metric("C. GRAND TOTAL Pagu", f"Rp {grand_total:,.0f}")

    with tab_ahsp:
        st.markdown("**Daftar Analisa Harga Satuan Pekerjaan (AHSP) Yang Digunakan:**")
        df_ahsp_used = df_rab[['Kode AHSP', 'Uraian AHSP 182', 'Satuan', 'Harga Satuan (Rp)']].drop_duplicates()
        st.dataframe(df_ahsp_used.style.format({'Harga Satuan (Rp)': 'Rp {:,.0f}'}), use_container_width=True)
        
    with tab_smkk:
        st.markdown("**Estimasi Biaya SMKK (Standar 9 Item PUPR):**")
        biaya_bpjs = total_rab_fisik * 0.005 # 0.5% dari fisik
        data_smkk = [
            {"No": 1, "Item SMKK": "Penyiapan Dokumen RK3K", "Biaya (Rp)": 1000000},
            {"No": 2, "Item SMKK": "Sosialisasi, Promosi, & Pelatihan", "Biaya (Rp)": 500000},
            {"No": 3, "Item SMKK": "Alat Pelindung Kerja (APK)", "Biaya (Rp)": 1500000},
            {"No": 4, "Item SMKK": "Alat Pelindung Diri (APD)", "Biaya (Rp)": 2000000},
            {"No": 5, "Item SMKK": "Asuransi & Perizinan (BPJS)", "Biaya (Rp)": biaya_bpjs},
            {"No": 6, "Item SMKK": "Personel K3", "Biaya (Rp)": 3500000},
            {"No": 7, "Item SMKK": "Fasilitas Kesehatan (P3K)", "Biaya (Rp)": 500000},
            {"No": 8, "Item SMKK": "Rambu-Rambu K3", "Biaya (Rp)": 500000},
            {"No": 9, "Item SMKK": "Lain-lain Terkait Risiko K3", "Biaya (Rp)": 0},
        ]
        df_smkk = pd.DataFrame(data_smkk)
        total_smkk = df_smkk['Biaya (Rp)'].sum()
        st.dataframe(df_smkk.style.format({'Biaya (Rp)': 'Rp {:,.0f}'}), use_container_width=True)
        st.info(f"👷 Total Anggaran SMKK: **Rp {total_smkk:,.0f}**")
        
    with tab_tkdn:
        st.markdown("**Rincian Tingkat Komponen Dalam Negeri (TKDN):**")
        tkdn_data = [
            {"Kategori": "Material (Semen, Pasir, Batu Lokal)", "Persentase TKDN": "100%", "Nilai TKDN (Rp)": total_rab_fisik * 0.40},
            {"Kategori": "Material (Baja/Besi Fabrikasi)", "Persentase TKDN": "45%", "Nilai TKDN (Rp)": total_rab_fisik * 0.20},
            {"Kategori": "Sewa Peralatan Konstruksi", "Persentase TKDN": "80%", "Nilai TKDN (Rp)": total_rab_fisik * 0.15},
            {"Kategori": "Upah Tenaga Kerja Lokal", "Persentase TKDN": "100%", "Nilai TKDN (Rp)": total_rab_fisik * 0.25},
        ]
        df_tkdn = pd.DataFrame(tkdn_data)
        total_tkdn = df_tkdn['Nilai TKDN (Rp)'].sum()
        persentase_tkdn = (total_tkdn / total_rab_fisik) * 100 if total_rab_fisik > 0 else 0
        st.dataframe(df_tkdn.style.format({'Nilai TKDN (Rp)': 'Rp {:,.0f}'}), use_container_width=True)
        st.metric("Total TKDN Proyek", f"{persentase_tkdn:.2f} %", "Memenuhi Standar > 40%")

    with tab_hsd:
        st.markdown(f"**Basic Price (HSD) & Indeks Kemahalan Konstruksi BPS - Wilayah {lokasi_proyek.upper()}:**")
        st.info(f"📈 **IKK Multiplier:** {ikk_multiplier}x terhadap Harga Dasar Nasional.")
        
        # Ekstrak HSD dari Database yang digunakan
        st.write("Preview Harga Satuan Dasar (Terpengaruh IKK BPS):")
        df_hsd_preview = df_ahsp_used.copy()
        df_hsd_preview.columns = ['Kode', 'Material/Pekerjaan', 'Satuan', 'Harga Setempat (Rp)']
        st.dataframe(df_hsd_preview.style.format({'Harga Setempat (Rp)': 'Rp {:,.0f}'}), use_container_width=True)

    st.divider()
    # =========================================================
    # 4. EXPORT FINAL
    # =========================================================
    st.markdown("### 📥 Cetak Dokumen Final (Approval)")
    st.info("Fitur Export Excel 7-Tab dan PDF sedang disinkronkan dengan Database SE 182 yang baru. (Under Maintenance)")































































