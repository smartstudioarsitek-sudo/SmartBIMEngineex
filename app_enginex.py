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
    # [MODIFIED] Tambahkan libs_beton dan libs_fem di sini
    try:
        from modules.struktur import libs_beton 
        from modules.struktur import libs_fem # [NEW] Modul FEM
    except ImportError:
        pass
    
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
sys.modules['libs_sni'] = libs_sni
sys.modules['libs_baja'] = libs_baja
sys.modules['libs_bridge'] = libs_bridge
sys.modules['libs_gempa'] = libs_gempa
# [NEW] Registrasi FEM & Beton agar AI bisa akses
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

st.markdown("""
<style>
    [data-testid="stSidebar"] {background-color: #F8FAFC; border-right: 1px solid #E2E8F0;}
    .stChatInput textarea {font-size: 16px !important;}
    .stDownloadButton button {width: 100%; border-radius: 6px; font-weight: 600;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .streamlit-expanderHeader {
        font-size: 14px; color: #64748B; background-color: #F1F5F9; border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. ENGINE EKSEKUSI KODE (SHARED MEMORY)
# ==========================================
if 'shared_execution_vars' not in st.session_state:
    st.session_state.shared_execution_vars = {}

def execute_generated_code(code_str, file_ifc_path=None):
    try:
        local_vars = st.session_state.shared_execution_vars.copy()
        
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
        
        # [NEW] Masukkan libs_fem dan libs_beton ke execution context AI
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
        return False

# ==========================================
# 4. FUNGSI EXPORT & UTILS
# ==========================================
def clean_text_for_report(text):
    clean = re.sub(r"```python.*?```", "", text, flags=re.DOTALL)
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    clean = re.sub(r'^"\d+",', '', clean, flags=re.MULTILINE)
    clean = clean.replace('","', ' | ').replace('"', '')
    clean = re.sub(r'\n\s*\n', '\n\n', clean)
    return clean.strip()

def create_docx(text):
    try:
        doc = docx.Document()
        doc.add_heading('Laporan ENGINEX', 0)
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

def create_pdf(text_content):
    if libs_pdf:
        try:
            pdf_bytes = libs_pdf.create_tabg_report(st.session_state, project_name="Proyek SmartBIM")
            return pdf_bytes
        except Exception:
            from fpdf import FPDF
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
    
    # [NEW] MENU NAVIGASI UTAMA (Untuk pindah ke FEM)
    st.markdown("### 🧭 Navigasi Menu")
    selected_menu = st.radio(
        "Pilih Modul:", 
        ["🤖 AI Assistant", "🌪️ Analisis Gempa (FEM)", "🏗️ Audit Struktur"],
        label_visibility="collapsed"
    )
    st.divider()

    # KONFIGURASI UMUM (Tetap ada di semua mode)
    if selected_menu == "🤖 AI Assistant":
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
            "gemini-flash-latest", "gemini-1.5-pro", "gemini-1.5-flash",
        ]
        model_name = st.selectbox("🧠 Model AI:", AVAILABLE_MODELS, index=0)
        
        # 3. MODE PERSONA
        st.markdown("### 🎭 Mode Persona")
        use_auto_pilot = st.checkbox("🤖 Auto-Pilot", value=True)
        daftar_ahli = get_persona_list()
        if use_auto_pilot:
            st.caption(f"📍 Ahli: **{st.session_state.current_expert_active}**")
        else:
            selected_expert = st.selectbox("👨‍💼 Pilih Spesialis:", daftar_ahli)
            st.session_state.current_expert_active = selected_expert
        
        # 4. MANAJEMEN PROYEK & FILE (Hanya di mode chat)
        st.markdown("### 📂 Proyek & File")
        projects = db.daftar_proyek()
        mode = st.radio("Mode:", ["Buka Proyek", "Buat Baru"], horizontal=True, label_visibility="collapsed")
        if mode == "Buat Baru":
            nama_proyek = st.text_input("Nama Proyek:", "Proyek-01")
        else:
            nama_proyek = st.selectbox("Pilih Proyek:", projects) if projects else "Default Project"
            
        uploaded_files = st.file_uploader("", type=["png","jpg","pdf","xlsx","docx","ifc","py"], accept_multiple_files=True)
        
        if st.button("🧹 Reset Chat"):
            db.clear_chat(nama_proyek, st.session_state.current_expert_active)
            st.session_state.processed_files.clear()
            st.session_state.shared_execution_vars = {}
            st.rerun()

    else:
        # Jika masuk mode Tools (FEM/Audit), tampilkan info simpel
        st.info(f"Modul Aktif: {selected_menu}")
        nama_proyek = "Engineering_Tools" # Dummy project name untuk tools

# ==========================================
# 6. LOGIKA TAMPILAN UTAMA (SWITCHING)
# ==========================================

# ------------------------------------------
# A. MODE 1: CHAT AI ASSISTANT (CODE LAMA)
# ------------------------------------------
if selected_menu == "🤖 AI Assistant":
    st.title(nama_proyek)
    st.caption(f"Ahli Aktif: {st.session_state.current_expert_active}")

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
                    with st.expander("🛠️ Lihat Detail Teknis"):
                        st.code(code_content, language='python')
                        st.download_button(
                            label="📥 Download Script", data=code_content, 
                            file_name=f"script_{download_btn_counter}.py", 
                            key=f"dl_btn_{download_btn_counter}"
                        )
                    execute_generated_code(code_content)
                else:
                    st.markdown(part)

    prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")

    if prompt:
        target_expert = st.session_state.current_expert_active
        if use_auto_pilot:
            # Simple router logic (simplified for brevity)
             target_expert = st.session_state.current_expert_active

        db.simpan_chat(nama_proyek, target_expert, "user", prompt)
        with st.chat_message("user"): st.markdown(prompt)

        full_prompt = [prompt]
        file_ifc_path = None
        if uploaded_files:
            for f in uploaded_files:
                if f.name not in st.session_state.processed_files:
                    if f.name.endswith(('.png','.jpg')): full_prompt.append(Image.open(f))
                    elif f.name.endswith('.pdf'):
                        reader = PyPDF2.PdfReader(f)
                        txt = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
                        full_prompt[0] += f"\n\n[FILE: {f.name}]\n{txt}"
                    elif f.name.endswith('.ifc'):
                        with open(f.name, "wb") as buffer: buffer.write(f.getbuffer())
                        file_ifc_path = f.name
                        full_prompt[0] += f"\n\n[SYSTEM]: User upload IFC: {f.name}."
                    st.session_state.processed_files.add(f.name)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    persona_instr = gems_persona.get(target_expert, gems_persona["👑 The GEMS Grandmaster"])
                    SYS = persona_instr + "\n[STRICT]: Use Markdown tables. Use Plotly. Python code in ```python blocks."
                    model = genai.GenerativeModel(model_name, system_instruction=SYS)
                    chat_hist = [{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history if h['content'] != prompt]
                    chat = model.start_chat(history=chat_hist)
                    response = chat.send_message(full_prompt)
                    
                    parts = re.split(r"(```python.*?```)", response.text, flags=re.DOTALL)
                    dl_ctr_new = 9000
                    for part in parts:
                        if part.startswith("```python"):
                            dl_ctr_new += 1
                            code_content = part.replace("```python", "").replace("```", "").strip()
                            with st.expander("🛠️ Detail Teknis"):
                                st.code(code_content, language='python')
                            execute_generated_code(code_content, file_ifc_path=file_ifc_path)
                        else:
                            st.markdown(part)
                    
                    db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                    
                    # Export Buttons
                    c1, c2, c3 = st.columns(3)
                    pdf_bytes = create_pdf(response.text)
                    if pdf_bytes: c1.download_button("📄 PDF", pdf_bytes, "Laporan.pdf")
                    doc_bytes = create_docx(response.text)
                    if doc_bytes: c2.download_button("📝 Word", doc_bytes, "Laporan.docx")
                except Exception as e:
                    st.error(f"Error: {e}")

# ------------------------------------------
# B. MODE 2: ANALISIS GEMPA (FEM) - [YANG ANDA MINTA]
# ------------------------------------------
elif selected_menu == "🌪️ Analisis Gempa (FEM)":
    st.header("🌪️ Analisis Gempa Dinamis (FEM Engine)")
    st.markdown("Fitur ini menggunakan **Finite Element Method** untuk menghitung karakteristik dinamis bangunan (OpenSees/Python-based).")

    # Layout Input
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("⚙️ Geometri")
            jml_lantai = st.number_input("Jumlah Lantai", 1, 50, 5)
            tinggi_lantai = st.number_input("Tinggi per Lantai (m)", 2.0, 6.0, 3.5)
        with c2:
            st.subheader("🏗️ Dimensi & Material")
            bentang_x = st.number_input("Bentang Arah X (m)", 3.0, 12.0, 6.0)
            bentang_y = st.number_input("Bentang Arah Y (m)", 3.0, 12.0, 6.0)
            fc_mutu = st.number_input("Mutu Beton (MPa)", 20, 60, 30)

    st.markdown("---")
    
    if st.button("🚀 RUN ANALISIS FEM (Modal Analysis)", type="primary"):
        if 'libs_fem' not in sys.modules:
            st.error("Modul `libs_fem` tidak ditemukan atau gagal dimuat.")
        else:
            with st.spinner("🔄 Membangun Matriks Kekakuan & Menghitung Eigenvalue..."):
                try:
                    # 1. Inisialisasi Engine
                    engine = libs_fem.OpenSeesEngine()
                    
                    # 2. Build Model
                    engine.build_simple_portal(bentang_x, bentang_y, tinggi_lantai, jml_lantai, fc_mutu)
                    
                    # 3. Run Analysis
                    df_modal = engine.run_modal_analysis(num_modes=3)
                    
                    st.success("✅ Analisis Selesai!")
                    
                    # 4. Tampilkan Hasil
                    st.subheader("📊 Hasil Modal Analysis (Mode Shapes)")
                    st.dataframe(df_modal, use_container_width=True)
                    
                    # 5. Visualisasi Chart (Plotly)
                    fig = px.bar(df_modal, x='Mode', y='Period (T) [detik]', 
                                 title="Perioda Alami Struktur (T)", color='Period (T) [detik]')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 6. Interpretasi
                    t1 = df_modal.iloc[0]['Period (T) [detik]']
                    st.info(f"💡 **Insight:** Perioda alami fundamental struktur adalah **{t1:.3f} detik**.")
                    
                except Exception as e:
                    st.error(f"❌ Terjadi Kesalahan pada Engine FEM: {e}")
                    st.caption("Detail Error: Pastikan library 'openseespy' atau dependencies terkait sudah terinstall.")

# ------------------------------------------
# C. MODE 3: AUDIT STRUKTUR (BETON)
# ------------------------------------------
elif selected_menu == "🏗️ Audit Struktur":
    st.header("🏗️ Audit Forensik Struktur (Beton Bertulang)")
    st.info("Pengecekan kapasitas kolom berdasarkan SNI 2847:2019 (Diagram Interaksi P-M).")

    # Cek ketersediaan modul
    if 'libs_beton' not in sys.modules:
        st.warning("⚠️ Modul `libs_beton` belum dimuat.")
    else:
        # Import class spesifik dari modul yang sudah diload
        from modules.struktur.libs_beton import SNIBeton2019

        # --- 1. INPUT DATA ---
        with st.expander("⚙️ Parameter Struktur & Beban", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Material**")
                fc_input = st.number_input("Mutu Beton (fc') [MPa]", value=25.0, step=5.0)
                fy_input = st.number_input("Mutu Baja (fy) [MPa]", value=420.0, step=10.0)
            with col2:
                st.markdown("**Dimensi Kolom**")
                b_input = st.number_input("Lebar (b) [mm]", value=400.0, step=50.0)
                h_input = st.number_input("Tinggi (h) [mm]", value=400.0, step=50.0)
            with col3:
                st.markdown("**Tulangan**")
                D_tul = st.number_input("Diameter Tulangan (D) [mm]", value=16.0, step=1.0)
                n_tul = st.number_input("Jumlah Batang Total", value=8, step=2)

            st.markdown("---")
            c_load1, c_load2 = st.columns(2)
            Pu_user = c_load1.number_input("Beban Aksial (Pu) [kN]", value=800.0)
            Mu_user = c_load2.number_input("Momen Lentur (Mu) [kNm]", value=150.0)

        # --- 2. ENGINE CALCULATION ---
        Ast_input = n_tul * 0.25 * 3.14159 * (D_tul ** 2)
        
        try:
            hasil_analisa = SNIBeton2019.analyze_column_capacity(
                b_input, h_input, fc_input, fy_input, Ast_input, Pu_user, Mu_user
            )
            pm_data = SNIBeton2019.generate_interaction_diagram(
                b_input, h_input, fc_input, fy_input, Ast_input
            )

            # --- 3. VISUALISASI ---
            st.divider()
            st.subheader("📊 Hasil Analisa Kapasitas")
            
            m1, m2, m3 = st.columns(3)
            status = hasil_analisa.get('Status', 'UNKNOWN')
            dcr = hasil_analisa.get('DCR_Ratio', 0)
            kap_max = hasil_analisa.get('Kapasitas_Max (kN)', 0)

            m1.metric("Status Keamanan", status, delta_color="normal" if status=="AMAN (SAFE)" else "inverse")
            m2.metric("Rasio DCR", f"{dcr} x")
            m3.metric("Kapasitas Aksial Max", f"{kap_max} kN")

            # Plot Diagram
            df_plot = pm_data['Plot_Data']
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_plot['M_Capacity'], y=df_plot['P_Capacity'], 
                fill='toself', fillcolor='rgba(0, 255, 0, 0.2)', line=dict(color='green', width=2),
                name='Zona Kapasitas Aman'
            ))
            status_color = 'blue' if status == "AMAN (SAFE)" else 'red'
            fig.add_trace(go.Scatter(
                x=[Mu_user], y=[Pu_user], mode='markers+text',
                marker=dict(color=status_color, size=15, symbol='x'),
                name='Beban Terjadi', text=[f"DCR: {dcr}"], textposition="top right"
            ))
            fig.update_layout(title="Diagram Interaksi P-M", xaxis_title="Momen (kNm)", yaxis_title="Axial (kN)", height=500)
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Gagal menghitung struktur: {e}")
