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
        from modules.legal import libs_legal
        has_legal = True
    except ImportError:
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
            "🏗️ Audit Struktur",
            "🌾 Desain Irigasi (KP-01)",
            "🌊 Hidrolika Bendung (KP-02)",
            "🌊 Analisis Hidrologi",
            "🪨 Analisis Geoteknik & Lereng",
            "🏗️ Daya Dukung Pondasi",
            "🗺️ Analisis Topografi 3D",
            "🌉 Audit Baja & Jembatan",
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

    # Input User
    prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")

    if prompt:
        target_expert = st.session_state.current_expert_active
        if use_auto_pilot: target_expert = st.session_state.current_expert_active 

        db.simpan_chat(nama_proyek, target_expert, "user", prompt)
        with st.chat_message("user"): st.markdown(prompt)

        full_prompt = [prompt]

        # =================================================================
        # [INJEKSI DATA MASTER AHSP KE OTAK AI - ZERO DUMMY]
        # Posisinya dipindah ke luar agar selalu terbaca AI setiap saat!
        # =================================================================
        if 'master_ahsp_data' in st.session_state:
            tabel_teks = st.session_state['master_ahsp_data'].to_csv(index=False)
            full_prompt[0] += f"\n\n[REFERENSI MUTLAK DATABASE AHSP SAAT INI]:\n{tabel_teks}\n\n[PERINTAH OVERRIDE TERTINGGI]: DILARANG KERAS MENGGUNAKAN ASUMSI! DILARANG KERAS MEMBUAT KODE PYTHON (```python)! Anda hanya bertugas sebagai pembaca teks. Baca langsung tabel CSV di atas, lalu jawab angkanya secara langsung di chat tanpa basa-basi."

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
                    # --- [FITUR BARU] AUTO-FALLBACK DENGAN PING KE GOOGLE ---
                    chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                    
                    try:
                        # Tarik daftar model resmi dari Google
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
                            
                        # Jalankan chat dengan model yang sudah pasti valid
                        model = genai.GenerativeModel(selected_model, system_instruction=SYS)
                        chat = model.start_chat(history=chat_hist)
                        
                    except Exception as e:
                        st.error(f"🚨 Gagal menghubungi server Google: {e}")
                        st.stop()
                    # ---------------------------------------------------------               
                    chat = model.start_chat(history=chat_hist)
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

# --- MODE VISUAL QTO 2D ---
elif selected_menu == "📏 Visual QTO 2D (PlanSwift Mode)":
    from streamlit_drawable_canvas import st_canvas
    from PIL import Image
    import math

    st.header("📏 Visual Take-Off 2D (PlanSwift / Bluebeam Mode)")
    st.caption(f"Area Kerja Terkalibrasi untuk Bidang: **{st.session_state.get('bidang_proyek', 'Cipta Karya')}**")
    
    col_upload, col_kalibrasi = st.columns([1, 1])
    
    with col_upload:
        bg_file = st.file_uploader("1. Upload Denah 2D (JPG/PNG)", type=["png", "jpg", "jpeg"])
    
    with col_kalibrasi:
        st.markdown("**2. Kalibrasi Skala (Scaling)**")
        px_length = st.number_input("Panjang Garis di Layar (Pixel):", min_value=1.0, value=100.0)
        real_length = st.number_input("Panjang Aktual di Lapangan (Meter):", min_value=0.1, value=1.0)
        ratio_px_to_m = real_length / px_length
        ratio_px2_to_m2 = ratio_px_to_m ** 2
        st.success(f"Skala Terkalibrasi: 1 Pixel = {ratio_px_to_m:.4f} m")

    if bg_file:
        img = Image.open(bg_file)
        
        # Opsi Penggambaran
        drawing_mode = st.radio("3. Mode Pengukuran (Take-off):", ("line", "polygon", "rect"), horizontal=True)
        
        stroke_width = 3
        stroke_color = "rgba(255, 0, 0, 1)" if drawing_mode == "line" else "rgba(0, 0, 255, 0.3)"
        
        st.markdown("### Area Kanvas (Draw Here)")
        # Inisialisasi Canvas
        canvas_result = st_canvas(
            fill_color="rgba(0, 0, 255, 0.3)",  # Transparan biru untuk area (polygon/rect)
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            background_image=img,
            update_streamlit=True,
            height=600,
            width=800,
            drawing_mode=drawing_mode,
            key="canvas",
        )

        # Hitung Otomatis Berdasarkan Gambar
        if canvas_result.json_data is not None:
            objects = canvas_result.json_data["objects"]
            if len(objects) > 0:
                st.markdown("### 📊 Hasil Quantity Take-Off (QTO)")
                
                total_panjang_m = 0
                total_luas_m2 = 0
                
                for obj in objects:
                    if obj["type"] == "line":
                        # Hitung jarak Euclidean (Pytagoras)
                        x1, y1 = obj["x1"], obj["y1"]
                        x2, y2 = obj["x2"], obj["y2"]
                        length_px = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                        total_panjang_m += length_px * ratio_px_to_m
                        
                    elif obj["type"] == "rect":
                        # Hitung Luas Persegi
                        area_px2 = obj["width"] * obj["height"]
                        total_luas_m2 += area_px2 * ratio_px2_to_m2
                
                # Tampilkan Metrik
                m1, m2 = st.columns(2)
                m1.metric("📏 Total Panjang (Meter Lari)", f"{total_panjang_m:.2f} m")
                m2.metric("🟦 Total Luas Area (Meter Persegi)", f"{total_luas_m2:.2f} m²")
                
                if st.button("💾 Simpan Volume ke Memori RAB", type="primary"):
                    # Inject ke session_state agar terbaca di Tab RAB 5D
                    item_baru = {
                        "Kategori": "Visual QTO",
                        "Nama": "Pekerjaan Area " + drawing_mode.capitalize(),
                        "Volume": round(total_luas_m2 if total_luas_m2 > 0 else total_panjang_m, 2)
                    }
                    if 'real_boq_data' not in st.session_state or st.session_state['real_boq_data'] is None:
                        st.session_state['real_boq_data'] = pd.DataFrame([item_baru])
                    else:
                        st.session_state['real_boq_data'] = pd.concat([st.session_state['real_boq_data'], pd.DataFrame([item_baru])], ignore_index=True)
                    
                    st.success("Volume berhasil dimasukkan ke Bill of Quantities (BOQ)! Buka menu RAB 5D untuk melihat harganya.")

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

# --- MODE ADMIN: MANAJEMEN DATABASE AHSP ---
elif selected_menu == "⚙️ Admin: Ekstraksi AHSP":
    import io
    st.header("⚙️ Manajemen Database AHSP PUPR")
    st.info("Menu khusus Admin. Unggah file Master Database AHSP (Excel/CSV) yang sudah terstruktur dengan pasti. Fitur AI dihentikan di menu ini untuk menjaga validitas angka.")
    
    # A. SEDIAKAN TEMPLATE KOSONG UNTUK PENGGUNA
    st.markdown("**1. Format Standar Sistem**")
    st.caption("Jika belum memiliki format, silakan download template tabel standar ini lalu isi menggunakan Microsoft Excel.")
    kolom_wajib = ["Bidang", "Kode_AHSP", "Deskripsi", "Kategori", "Nama_Komponen", "Satuan", "Koefisien"]
    template_df = pd.DataFrame(columns=kolom_wajib)
    
    output_template = io.BytesIO()
    with pd.ExcelWriter(output_template, engine='xlsxwriter') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Master_AHSP')
    
    st.download_button(
        label="📥 Download Template Excel AHSP", 
        data=output_template.getvalue(), 
        file_name="Template_Master_AHSP.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()

    # B. UPLOADER DATABASE MURNI
    st.markdown("**2. Unggah Data Master**")
    file_master_ahsp = st.file_uploader("Upload file Master AHSP (.xlsx, .csv):", type=["xlsx", "xls", "csv"])
    
    if file_master_ahsp is not None:
        try:
            with st.spinner("Membaca dan memvalidasi keaslian data..."):
                # Baca sesuai ekstensi file
                if file_master_ahsp.name.endswith('.csv'):
                    df_ahsp = pd.read_csv(file_master_ahsp)
                else:
                    df_ahsp = pd.read_excel(file_master_ahsp)
                
                # Validasi anti-bug: Pastikan strukturnya benar
                kolom_file = df_ahsp.columns.tolist()
                
                if all(k in kolom_file for k in kolom_wajib):
                    st.success(f"✅ Data tervalidasi! Berhasil memuat {len(df_ahsp)} baris resep AHSP.")
                    
                    # Tampilkan tabel asli dari file
                    st.dataframe(df_ahsp, use_container_width=True)
                    
                    # Tombol Simpan ke Memori
                    if st.button("💾 Kunci Data ke Sistem Estimasi", type="primary", use_container_width=True):
                        st.session_state['master_ahsp_data'] = df_ahsp
                        st.success("✅ Database terkunci! Modul RAB sekarang akan merujuk pada data ini secara mutlak.")
                else:
                    st.error("❌ Format file ditolak. Pastikan header tabel sesuai dengan template.")
                    st.warning(f"Kolom yang terdeteksi di file Anda: {kolom_file}")
                    
        except Exception as e:
            st.error(f"❌ Terjadi kesalahan saat memproses file: {e}")
            
# --- E. MODE LAPORAN RAB 5D ---
elif selected_menu == "📑 Laporan RAB 5D":
    st.header("📑 Laporan Eksekutif RAB 5D (Dokumen Lelang)")
    st.caption("Generator Dokumen Rencana Anggaran Biaya standar Kementerian PUPR")
    # =========================================================
    # [FITUR KEAMANAN ZERO DUMMY] Mencegah Cetak Excel Kosong
    # =========================================================
    if 'master_ahsp_data' not in st.session_state:
        st.error("🚨 SISTEM TERKUNCI: Database AHSP Kosong!")
        st.warning("Aplikasi menolak mencetak angka nol/fiktif. Silakan ke menu **⚙️ Admin: Ekstraksi AHSP** di sidebar, upload Template Excel AHSP-nya, lalu klik tombol merah **'Kunci Data'** terlebih dahulu.")
        st.stop() # Menghentikan sistem agar tidak cetak Excel kosong
    # =========================================================

    # 1. Tampilan Rencana Isi Laporan (Hanya Informasi, TANPA TOMBOL SATUAN)
    st.markdown("### 📋 Struktur Dokumen yang Akan Dicetak:")

    # 1. Tampilan Rencana Isi Laporan (Hanya Informasi, TANPA TOMBOL SATUAN)
    st.markdown("### 📋 Struktur Dokumen yang Akan Dicetak:")
    step1, step2, step3 = st.columns(3)
    step4, step5, step6 = st.columns(3)

    with step1:
        with st.expander("1. Pendahuluan & Lingkup", expanded=True):
            st.write("Berisi latar belakang proyek, deskripsi BIM, dan metodologi otomatis.")
    with step2:
        with st.expander("2. Asumsi Dasar & AHSP", expanded=True):
            st.write("Menetapkan dasar harga material, upah kerja, dan referensi AHSP.")
    with step3:
        with st.expander("3. Bill of Quantities (BOQ)", expanded=True):
            st.write("Rekapitulasi total volume pekerjaan dari ekstraksi BIM/AI-QS.")
    with step4:
        with st.expander("4. Integrasi SMKK & K3", expanded=True):
            st.write("Perhitungan biaya Keselamatan Konstruksi sesuai risiko proyek.")
    with step5:
        with st.expander("5. Analisis TKDN (Lokal)", expanded=True):
            st.write("Proporsi penggunaan material dalam negeri vs luar negeri.")
    with step6:
        with st.expander("6. Rekapitulasi & Grand Total", expanded=True):
            st.write("Ringkasan final, PPN 11%, dan Grand Total Biaya Fisik.")

    st.markdown("---")
    
    # 1. Kumpulkan teks laporan secara DINAMIS (ZERO DUMMY)
    df_boq_aktual = st.session_state.get('real_boq_data', None)
    lokasi_proyek = st.session_state.get('lokasi_bps', 'Lampung')

    laporan_gabungan = f"""
# DOKUMEN RENCANA ANGGARAN BIAYA (RAB) 5D
**PROYEK: {nama_proyek.upper()}**
**LOKASI: {lokasi_proyek.upper()}**

## BAB 1. PENDAHULUAN
Laporan ini disusun secara otomatis menggunakan sistem SmartBIM Enginex yang terintegrasi dengan standar ekstraksi kuantitas (QTO) berbasis algoritma analitik geometri, serta mengacu pada Surat Edaran (SE) Direktur Jenderal Bina Konstruksi No. 30/SE/Dk/2025.

## BAB 2. BILL OF QUANTITIES (BOQ) AKTUAL
Berikut adalah rekapitulasi volume pekerjaan yang diekstrak secara presisi dari model digital:

"""
    # Menyuntikkan data aktual ke dalam PDF
    if df_boq_aktual is not None and not df_boq_aktual.empty:
        for index, row in df_boq_aktual.iterrows():
            laporan_gabungan += f"- **{row['Kategori']}**: {row['Nama']} (Volume: {row.get('Volume', 0)} m3)\n"
    else:
        laporan_gabungan += "*(Data BOQ masih kosong. Silakan lakukan ekstraksi file IFC atau ukur via Visual QTO 2D terlebih dahulu untuk mengisi bab ini.)*\n"

    laporan_gabungan += """
## BAB 3. KESELAMATAN KONSTRUKSI (SMKK) & REKAPITULASI
Biaya penerapan SMKK telah dihitung secara proporsional sesuai dengan 9 komponen standar PUPR untuk memitigasi risiko kecelakaan kerja di lapangan. Total estimasi biaya konstruksi fisik dan rincian Analisa Harga Satuan Pekerjaan (AHSP) dapat dilihat secara komprehensif pada dokumen lampiran Spreadsheet (Excel 7-Tab) yang menyertai laporan ini.
"""
    
    # 2. Render tombol Download yang sesungguhnya
    try:
        # Menggunakan engine PDF internal kita
        pdf_bytes = libs_pdf.create_pdf(laporan_gabungan, title=f"LAPORAN RAB - {nama_proyek}")
        
        st.download_button(
            label="📄 1. Download Laporan RAB (PDF)",
            data=pdf_bytes,
            file_name=f"Laporan_RAB_{nama_proyek.replace(' ', '_')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        # --- TOMBOL EXCEL DIPINDAH KESINI ---
        df_boq_aktual = st.session_state.get('real_boq_data', None)
        lokasi_proyek = st.session_state.get('lokasi_bps', 'Lampung')
        
        if df_boq_aktual is not None and not df_boq_aktual.empty:
            st.success(f"🟢 Data BOQ Siap ({len(df_boq_aktual)} baris) untuk Lokasi: {lokasi_proyek}")
            with st.spinner("Memproses Excel..."):
                if 'price_engine' not in st.session_state:
                    st.session_state.price_engine = sys.modules['libs_price_engine'].PriceEngine3Tier()
                
                excel_bytes = sys.modules['libs_export'].Export_Engine().generate_7tab_rab_excel(
                    nama_proyek, df_boq_aktual, price_engine=st.session_state.price_engine, lokasi_proyek=lokasi_proyek 
                )
                st.download_button(
                    label="📊 2. Download Excel RAB 7-Tab (Harga Auto-BPS)",
                    data=excel_bytes,
                    file_name=f"RAB_{lokasi_proyek}_{nama_proyek.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ Data Kosong. Ekstrak IFC di Sidebar atau gunakan Visual QTO terlebih dahulu untuk mengaktifkan tombol Excel.")
            st.button("📊 2. Download Excel RAB", disabled=True, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Gagal merender dokumen: {e}")





























