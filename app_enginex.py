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
# 1. IMPORT LIBRARY ENGINEERING (THE FIX)
# ==========================================
# Disini perbaikannya. Kita panggil dari dalam folder modules.

try:
    # A. Modul Core (Otak & Memori)
    from core.backend_enginex import EnginexBackend
    from core.persona import gems_persona, get_persona_list

    # B. Modul Struktur (Sesuai GitHub: modules/struktur)
    from modules.struktur import libs_sni, libs_baja, libs_bridge, libs_gempa
    # (Optional: Geoteknik & Pondasi jika file sudah ada di folder geotek)
    # Jika belum ada di github, comment dulu baris bawah ini biar gak error
    # from modules.geotek import libs_geoteknik, libs_pondasi 

    # C. Modul Water (Sesuai GitHub: modules/water)
    # Pastikan file libs_hidrologi.py dll sudah ada di folder water
    from modules.water import libs_hidrologi, libs_irigasi, libs_jiat, libs_bendung

    # D. Modul Cost (Sesuai GitHub: modules/cost)
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research

    # E. Modul Utils (Sesuai GitHub: modules/utils)
    from modules.utils import libs_pdf, libs_export, libs_bim_importer
    
    # F. Modul Arsitektur (Sesuai GitHub: modules/arch)
    from modules.arch import libs_arch, libs_zoning, libs_green

except ImportError as e:
    # Error Handling yang informatif
    st.error(f"⚠️ **SISTEM ERROR: Gagal Import Modul**")
    st.code(str(e), language='bash')
    st.info("💡 **Diagnosa:** Python tidak bisa menemukan file di folder modules. Pastikan nama file di `import` sama persis dengan nama file di GitHub.")
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
    .main-header {font-size: 30px; font-weight: bold; color: #1E3A8A; margin-bottom: 10px;}
    [data-testid="stSidebar"] {background-color: #f8f9fa;}
    .stChatInput textarea {font-size: 16px !important;}
    .stChatMessage .avatar {background-color: #1E3A8A; color: white;}
    .auto-pilot-msg {background-color: #e0f7fa; border-left: 5px solid #00acc1; padding: 10px; border-radius: 5px; color: #006064; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. ENGINE EKSEKUSI KODE (LOGIC INJECTION)
# ==========================================
def execute_generated_code(code_str, file_ifc_path=None):
    """
    Menjalankan kode Python dari AI dan menyuntikkan Library kita ke dalamnya.
    """
    try:
        # KOTAK PERKAKAS: Kita kasih 'jalan pintas' ke library yang sudah diimport di atas
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
        
        # Inject IFC File jika ada
        if file_ifc_path:
            local_vars["file_ifc_user"] = file_ifc_path
        
        # Eksekusi
        exec(code_str, {}, local_vars)
        return True
    except Exception as e:
        st.error(f"⚠️ Gagal Eksekusi Kode: {e}")
        with st.expander("Lihat Kode Error"):
            st.code(code_str, language='python')
        return False

# ==========================================
# 4. FUNGSI UTILITAS (DOCX & EXCEL)
# ==========================================
def create_docx_from_text(text_content):
    try:
        doc = docx.Document()
        doc.add_heading('Laporan Output ENGINEX', 0)
        for line in text_content.split('\n'):
            clean = line.strip()
            if clean.startswith('## '): doc.add_heading(clean.replace('## ', ''), level=2)
            elif clean.startswith('### '): doc.add_heading(clean.replace('### ', ''), level=3)
            elif clean.startswith('- '): 
                try: doc.add_paragraph(clean, style='List Bullet')
                except: doc.add_paragraph(clean)
            elif clean: doc.add_paragraph(clean)
        bio = io.BytesIO()
        doc.save(bio)
        bio.seek(0)
        return bio
    except: return None

def extract_table_to_excel(text_content):
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

# ==========================================
# 5. SIDEBAR & SETUP
# ==========================================
# Init Session
if 'backend' not in st.session_state: st.session_state.backend = EnginexBackend()
if 'processed_files' not in st.session_state: st.session_state.processed_files = set()
if 'current_expert_active' not in st.session_state: st.session_state.current_expert_active = "👑 The GEMS Grandmaster"

db = st.session_state.backend

with st.sidebar:
    st.title("🏗️ ENGINEX ULTIMATE")
    
    # API Key Handling
    api_key_input = st.text_input("🔑 API Key:", type="password")
    raw_key = api_key_input if api_key_input else st.secrets.get("GOOGLE_API_KEY")
    
    if not raw_key:
        st.warning("⚠️ Masukkan API Key.")
        st.stop()
    
    genai.configure(api_key=raw_key, transport="rest")
    
    # Model Selection
    model_opts = ["gemini-1.5-flash", "gemini-1.5-pro"]
    selected_model = st.selectbox("🧠 Model AI:", model_opts)
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot", value=True)
    
    st.divider()
    
    # Proyek
    projects = db.daftar_proyek()
    mode_prj = st.radio("Proyek:", ["Baru", "Buka"], horizontal=True)
    nama_proyek = st.text_input("Nama:", "Proyek 1") if mode_prj == "Baru" else st.selectbox("Pilih:", projects)

# ==========================================
# 6. UPLOAD & MAIN AREA
# ==========================================
def process_file(f):
    name = f.name.lower()
    if name.endswith(('.png','.jpg')): return "image", Image.open(f)
    elif name.endswith('.pdf'): 
        reader = PyPDF2.PdfReader(f)
        return "text", "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    elif name.endswith(('.xlsx','.xls')):
        return "text", pd.read_excel(f).head(50).to_markdown()
    elif name.endswith('.ifc'): return "ifc_bytes", f
    return "unknown", None

with st.sidebar:
    st.markdown("### 📂 Upload")
    uploaded_files = st.file_uploader("File:", accept_multiple_files=True)
    if st.button("🧹 Reset"):
        db.clear_chat(nama_proyek, st.session_state.current_expert_active)
        st.session_state.processed_files.clear()
        st.rerun()

# Header & Chat History
st.markdown(f'<div class="main-header">{nama_proyek}</div>', unsafe_allow_html=True)
current_persona = st.session_state.current_expert_active
history = db.get_chat_history(nama_proyek, current_persona)

for msg in history:
    with st.chat_message(msg['role']): st.markdown(msg['content'])

# Input & Logic
prompt = st.chat_input(f"Diskusi dengan {current_persona}...")

if prompt:
    # Auto Pilot Logic
    target_expert = current_persona
    if use_auto_pilot:
        with st.status("🧠 Menganalisis...", expanded=True) as s:
            try:
                router = genai.GenerativeModel("gemini-1.5-flash")
                list_ahli = list(gems_persona.keys())
                res = router.generate_content(f"Pertanyaan: '{prompt}'. Siapa ahli paling tepat dari: {list_ahli}? Jawab HANYA nama.")
                sug = res.text.strip()
                if sug in list_ahli: target_expert = sug; st.session_state.current_expert_active = sug
                s.write(f"Dialihkan ke: **{target_expert}**")
            except: pass

    db.simpan_chat(nama_proyek, target_expert, "user", prompt)
    with st.chat_message("user"): st.markdown(prompt)

    # Context Building
    full_prompt = [prompt]
    file_ifc_obj = None
    if uploaded_files:
        for f in uploaded_files:
            if f.name not in st.session_state.processed_files:
                tipe, konten = process_file(f)
                if tipe == "image": 
                    full_prompt.append(konten)
                    with st.chat_message("user"): st.image(f, width=200)
                elif tipe == "text":
                    full_prompt[0] += f"\n\n[FILE: {f.name}]\n{konten}"
                    with st.chat_message("user"): st.caption(f"📄 {f.name} terbaca")
                elif tipe == "ifc_bytes":
                    file_ifc_obj = f
                    with st.chat_message("user"): st.caption(f"🏗️ Model BIM {f.name} siap")
                st.session_state.processed_files.add(f.name)

    # AI Response
    with st.chat_message("assistant"):
        with st.spinner(f"{target_expert} sedang bekerja..."):
            try:
                # Instruksi Visualisasi
                VISUAL_PROMPT = """
                \n[ATURAN CODE]:
                1. Jika diminta hitungan/grafik, TULIS KODE PYTHON (```python).
                2. Gunakan library custom: libs_sni, libs_irigasi, libs_hidrologi, libs_rab_engine.
                3. Tampilkan grafik dengan `st.pyplot(plt.gcf())`.
                4. Tampilkan tabel dengan `st.dataframe(df)`.
                """
                
                model = genai.GenerativeModel(selected_model, system_instruction=gems_persona[target_expert] + VISUAL_PROMPT)
                chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                chat = model.start_chat(history=chat_hist)
                response = chat.send_message(full_prompt)
                
                st.markdown(response.text)
                db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                
                # Eksekusi Kode
                code_matches = re.findall(r"```python(.*?)```", response.text, re.DOTALL)
                for code in code_matches:
                    st.markdown("---")
                    execute_generated_code(code, file_ifc_path=file_ifc_obj)
                
                # Download
                c1, c2 = st.columns(2)
                doc = create_docx_from_text(response.text)
                if doc: c1.download_button("📄 Laporan (.docx)", doc, "Laporan.docx")
                xl = extract_table_to_excel(response.text)
                if xl: c2.download_button("📊 Data (.xlsx)", xl, "Data.xlsx")
                
            except Exception as e:
                st.error(f"Error: {e}")
