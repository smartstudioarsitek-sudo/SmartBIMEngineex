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

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(
    page_title="ENGINEX Ultimate", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Custom untuk Tampilan Profesional
st.markdown("""
<style>
    .main-header {font-size: 30px; font-weight: bold; color: #1E3A8A; margin-bottom: 10px;}
    [data-testid="stSidebar"] {background-color: #f8f9fa;}
    .stChatInput textarea {font-size: 16px !important;}
    .stChatMessage .avatar {background-color: #1E3A8A; color: white;}
    .stDownloadButton button {width: 100%; border-radius: 8px; font-weight: bold;}
    .auto-pilot-msg {
        background-color: #e0f7fa; border-left: 5px solid #00acc1;
        padding: 10px; margin-bottom: 10px; border-radius: 5px;
        color: #006064; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. IMPORT MODULES (CORE & ENGINEERING)
# ==========================================
# Bagian ini sangat krusial. Kita mengimpor "Otak" engineering dari folder modules.

try:
    # A. Modul Core (Database & Persona)
    from core.backend_enginex import EnginexBackend
    from core.persona import gems_persona, get_persona_list

    # B. Modul Struktur (Sipil Keras)
    from modules.struktur import libs_sni, libs_baja, libs_bridge, libs_gempa
    from modules.geotek import libs_geoteknik, libs_pondasi

    # C. Modul Water Resources (Hasil Konsolidasi Baru)
    # File ini berisi gabungan HEC-RAS, Mock, Banjir, dll
    from modules.water import libs_hidrologi, libs_irigasi, libs_bendung, libs_jiat

    # D. Modul Cost & Manajemen (Hasil Konsolidasi Baru)
    # File ini berisi RAB Saluran, Box Culvert, AHSP
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research

    # E. Modul Arsitektur & Lingkungan
    from modules.arch import libs_arch, libs_zoning, libs_green

    # F. Modul Utils (Pendukung)
    from modules.utils import libs_pdf, libs_export, libs_bim_importer

except ImportError as e:
    st.error(f"⚠️ **CRITICAL SYSTEM ERROR** ⚠️\n\nGagal memuat modul engineering.\nDetail Error: `{e}`")
    st.info("💡 **Solusi:** Pastikan struktur folder `modules/water`, `modules/cost` dll sudah benar dan memiliki file `__init__.py` kosong di dalamnya.")
    st.stop()

# ==========================================
# 3. INISIALISASI SESSION STATE
# ==========================================
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state:
    st.session_state.current_expert_active = "👑 The GEMS Grandmaster"
if 'backend' not in st.session_state:
    st.session_state.backend = EnginexBackend() # Inisialisasi Database

db = st.session_state.backend

# ==========================================
# 4. FUNGSI UTILITAS (EXPORT & PLOTTER)
# ==========================================

def create_docx_from_text(text_content):
    """Konversi teks chat ke dokumen Word."""
    try:
        doc = docx.Document()
        doc.add_heading('Laporan Output ENGINEX', 0)
        for line in text_content.split('\n'):
            clean = line.strip()
            if clean.startswith('## '): doc.add_heading(clean.replace('## ', ''), level=2)
            elif clean.startswith('### '): doc.add_heading(clean.replace('### ', ''), level=3)
            elif clean.startswith('- ') or clean.startswith('* '): 
                try: doc.add_paragraph(clean, style='List Bullet')
                except: doc.add_paragraph(clean)
            elif clean: doc.add_paragraph(clean)
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        return bio
    except: return None

def extract_table_to_excel(text_content):
    """Ekstrak tabel Markdown ke Excel."""
    try:
        lines = text_content.split('\n')
        data = []
        for line in lines:
            if "|" in line and "---" not in line:
                row = [c.strip() for c in line.split('|') if c.strip()]
                if row: data.append(row)
        if len(data) < 2: return None
        df = pd.DataFrame(data[1:], columns=data[0])
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        out.seek(0)
        return out
    except: return None

def execute_generated_code(code_str, file_ifc_path=None):
    """
    [JANTUNG APLIKASI]
    Mengeksekusi kode Python yang dibuat oleh AI.
    Di sini kita menyuntikkan semua library engineering agar bisa dipanggil AI.
    """
    try:
        # KOTAK PERKAKAS (Local Variables untuk fungsi exec)
        local_vars = {
            "pd": pd, "np": np, "plt": plt, "st": st,
            
            # --- LIBRARY STRUKTUR ---
            "libs_sni": libs_sni, "libs_baja": libs_baja, 
            "libs_bridge": libs_bridge, "libs_gempa": libs_gempa,
            "libs_geoteknik": libs_geoteknik, "libs_pondasi": libs_pondasi,
            
            # --- LIBRARY WATER (BARU) ---
            "libs_hidrologi": libs_hidrologi,   # Untuk Banjir & Mock
            "libs_irigasi": libs_irigasi,       # Untuk Saluran & DXF
            "libs_bendung": libs_bendung,       # Untuk Bendung
            "libs_jiat": libs_jiat,             # Untuk Pipa & Pompa
            
            # --- LIBRARY COST (BARU) ---
            "libs_ahsp": libs_ahsp,
            "libs_rab_engine": libs_rab_engine, # Untuk Volume Fisik
            "libs_optimizer": libs_optimizer,
            "libs_research": libs_research,
            
            # --- LIBRARY ARCH & UTILS ---
            "libs_arch": libs_arch, "libs_zoning": libs_zoning,
            "libs_green": libs_green, "libs_pdf": libs_pdf, 
            "libs_export": libs_export, "libs_bim_importer": libs_bim_importer
        }
        
        # Inject File IFC jika ada (Khusus untuk modul BIM)
        if file_ifc_path:
            local_vars["file_ifc_user"] = file_ifc_path

        # Jalankan Kode
        exec(code_str, {}, local_vars)
        return True
    except Exception as e:
        st.error(f"⚠️ Eksekusi Kode Gagal: {e}")
        with st.expander("🔍 Lihat Kode Error"):
            st.code(code_str, language='python')
        return False

# ==========================================
# 5. SIDEBAR: PENGATURAN & INPUT
# ==========================================
with st.sidebar:
    st.title("🏗️ ENGINEX ULTIMATE")
    st.caption("v12.0 | Integrated System")
    
    # API KEY
    api_key_input = st.text_input("🔑 API Key:", type="password")
    raw_key = api_key_input if api_key_input else st.secrets.get("GOOGLE_API_KEY")
    
    if not raw_key:
        st.warning("⚠️ Masukkan API Key Google AI Studio.")
        st.stop()
    
    # Konfigurasi Gemini
    try:
        genai.configure(api_key=raw_key, transport="rest")
    except Exception as e:
        st.error(f"API Error: {e}")

    # Pilihan Model
    model_opts = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"] # Hardcoded fallback
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if models: model_opts = sorted(models, key=lambda x: 'pro' in x)
    except: pass
    
    selected_model = st.selectbox("🧠 Model AI:", model_opts, index=0)
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot (Smart Router)", value=True)
    
    st.divider()
    
    # Manajemen Proyek
    projects = db.daftar_proyek()
    mode_prj = st.radio("Mode Proyek:", ["Baru", "Buka"], horizontal=True)
    if mode_prj == "Baru":
        nama_proyek = st.text_input("Nama Proyek:", "DED Bendung 2026")
    else:
        nama_proyek = st.selectbox("Pilih Proyek:", projects) if projects else "Default Project"

# ==========================================
# 6. FILE UPLOAD & PROCESSING
# ==========================================
def process_file(uploaded_file):
    if not uploaded_file: return None, None
    name = uploaded_file.name.lower()
    
    try:
        if name.endswith(('.png', '.jpg', '.jpeg')):
            return "image", Image.open(uploaded_file)
        elif name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(uploaded_file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            return "text", text
        elif name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
            return "text", f"[DATA EXCEL]\n{df.head(30).to_markdown()}"
        elif name.endswith('.docx'):
            doc = docx.Document(uploaded_file)
            return "text", "\n".join([p.text for p in doc.paragraphs])
        elif name.endswith('.ifc'):
            return "ifc_bytes", uploaded_file # Return object langsung untuk BIM Engine
        elif name.endswith('.py'):
            return "text", uploaded_file.getvalue().decode("utf-8")
    except Exception as e:
        return "error", str(e)
    return "unknown", None

with st.sidebar:
    st.markdown("### 📂 Input Data")
    uploaded_files = st.file_uploader("Upload File (PDF/Excel/Gambar/IFC):", accept_multiple_files=True)
    
    if st.button("🧹 Hapus Chat"):
        db.clear_chat(nama_proyek, st.session_state.current_expert_active)
        st.session_state.processed_files.clear()
        st.rerun()

# ==========================================
# 7. LOGIKA UTAMA CHAT (MAIN LOOP)
# ==========================================
st.markdown(f'<div class="main-header">{nama_proyek}</div>', unsafe_allow_html=True)

# Tampilkan History Chat
current_persona = st.session_state.current_expert_active
history = db.get_chat_history(nama_proyek, current_persona)

for msg in history:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

# Input User
prompt = st.chat_input(f"Diskusi dengan {current_persona}...")

if prompt:
    # 1. Tentukan Ahli (Auto-Pilot)
    target_expert = current_persona
    if use_auto_pilot:
        with st.status("🧠 Menganalisis kebutuhan...", expanded=True) as s:
            try:
                # Simple Router Logic
                router = genai.GenerativeModel("gemini-1.5-flash")
                list_ahli = list(gems_persona.keys())
                res = router.generate_content(f"Pertanyaan: '{prompt}'. Siapa ahli yang paling tepat menjawab dari daftar ini: {list_ahli}? Jawab HANYA nama ahli.")
                sug = res.text.strip()
                if sug in list_ahli: 
                    target_expert = sug
                    st.session_state.current_expert_active = target_expert
                    s.write(f"Dialihkan ke: **{target_expert}**")
            except: pass
            
    # 2. Simpan Chat User
    db.simpan_chat(nama_proyek, target_expert, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)
    
    # 3. Siapkan Konteks & File
    full_prompt = [prompt]
    file_ifc_obj = None # Placeholder untuk BIM
    
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.processed_files:
                tipe, konten = process_file(f)
                if tipe == "image": 
                    full_prompt.append(konten)
                    with st.chat_message("user"): st.image(f, width=200)
                elif tipe == "text":
                    full_prompt[0] += f"\n\n[DATA FILE: {f.name}]\n{konten}"
                    with st.chat_message("user"): st.caption(f"📄 {f.name} terbaca")
                elif tipe == "ifc_bytes":
                    file_ifc_obj = f # Simpan referensi untuk dikirim ke Python Engine
                    with st.chat_message("user"): st.caption(f"🏗️ Model BIM {f.name} siap diproses")
                
                st.session_state.processed_files.add(f.name)

    # 4. Generate Jawaban AI
    with st.chat_message("assistant"):
        with st.spinner(f"{target_expert} sedang bekerja..."):
            try:
                # Instruksi Khusus Python
                SYS_PROMPT = gems_persona[target_expert] + """
                \n[INSTRUKSI VISUALISASI & HITUNGAN]:
                1. Jika diminta menghitung/grafik, WAJIB menulis kode Python (```python).
                2. Gunakan library custom yang tersedia: `libs_hidrologi` (banjir), `libs_irigasi` (saluran), `libs_rab_engine` (biaya), `libs_sni` (beton).
                3. Untuk menampilkan grafik: akhiri dengan `st.pyplot(plt.gcf())`.
                4. Untuk menampilkan tabel: akhiri dengan `st.dataframe(df)`.
                5. Jangan lupa import library yang dibutuhkan di awal blok kode.
                """
                
                model = genai.GenerativeModel(selected_model, system_instruction=SYS_PROMPT)
                
                # Build History for Context
                chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                
                chat = model.start_chat(history=chat_hist)
                response = chat.send_message(full_prompt)
                
                # Tampilkan Teks Jawaban
                st.markdown(response.text)
                db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                
                # 5. Eksekusi Kode Python (Jika Ada)
                # Regex untuk mencari blok kode ```python ... ```
                code_matches = re.findall(r"```python(.*?)```", response.text, re.DOTALL)
                for code in code_matches:
                    st.markdown("---")
                    st.caption("⚙️ **Engine Output (Hasil Perhitungan/Grafik):**")
                    # Pass file IFC object jika ada, agar bisa dibaca library BIM
                    execute_generated_code(code, file_ifc_path=file_ifc_obj)
                
                # 6. Tombol Download
                c1, c2 = st.columns(2)
                docx = create_docx_from_text(response.text)
                if docx: c1.download_button("📄 Download Laporan (.docx)", docx, "Laporan_Enginex.docx")
                
                xl = extract_table_to_excel(response.text)
                if xl: c2.download_button("📊 Download Data (.xlsx)", xl, "Data_Enginex.xlsx")
                
            except Exception as e:
                st.error(f"Terjadi Kesalahan: {e}")
