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
# 1. KONFIGURASI HALAMAN & SECURITY
# ==========================================
st.set_page_config(
    page_title="ENGINEX Ultimate", 
    page_icon="🏗️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Professional
st.markdown("""
<style>
    [data-testid="stSidebar"] {background-color: #F8FAFC; border-right: 1px solid #E2E8F0;}
    .stChatInput textarea {font-size: 16px !important;}
    .stDownloadButton button {width: 100%; border-radius: 6px; font-weight: 600;}
    
    /* Sembunyikan Elemen Default */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Styling Expander */
    .streamlit-expanderHeader {
        font-size: 14px;
        color: #64748B;
        background-color: #F1F5F9;
        border-radius: 8px;
    }
    
    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. IMPORT LIBRARY ENGINEERING (MODULAR)
# ==========================================
try:
    # A. Core Modules
    from core.backend_enginex import EnginexBackend
    from core.persona import gems_persona, get_persona_list

    # B. Engineering Modules
    # Struktur
    from modules.struktur import libs_sni, libs_baja, libs_bridge, libs_gempa, libs_beton
    
    # Water Resources
    from modules.water import libs_hidrologi, libs_irigasi, libs_jiat, libs_bendung
    
    # Cost & Management
    from modules.cost import libs_ahsp, libs_rab_engine, libs_optimizer, libs_research
    
    # Architecture & Environment
    from modules.arch import libs_arch, libs_zoning, libs_green
    
    # Utils
    from modules.utils import libs_pdf, libs_export, libs_bim_importer
    
    # Optional Modules (Geoteknik & FEM)
    try: 
        from modules.geotek import libs_geoteknik, libs_pondasi
        has_geotek = True
    except ImportError: 
        has_geotek = False

    try:
        from modules.struktur import libs_fem
        has_fem = True
    except ImportError:
        has_fem = False

except ImportError as e:
    st.error(f"⚠️ **CRITICAL SYSTEM ERROR**")
    st.write(f"Gagal memuat modul engineering. Pesan Error: `{e}`")
    st.info("Pastikan struktur folder modules/ sudah benar dan file __init__.py ada.")
    st.stop()

# REGISTRASI MODUL KE SYSTEM (Agar bisa dipanggil exec)
sys.modules['libs_sni'] = libs_sni
sys.modules['libs_baja'] = libs_baja
sys.modules['libs_bridge'] = libs_bridge
sys.modules['libs_gempa'] = libs_gempa
sys.modules['libs_beton'] = libs_beton
if has_fem: sys.modules['libs_fem'] = libs_fem

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
# 3. ENGINE UTILS & EXECUTION
# ==========================================
if 'shared_execution_vars' not in st.session_state:
    st.session_state.shared_execution_vars = {}

def execute_generated_code(code_str, file_ifc_path=None):
    """Menjalankan kode Python AI dengan Memori Persisten & Plotly."""
    try:
        local_vars = st.session_state.shared_execution_vars.copy()
        
        library_kits = {
            "pd": pd, "np": np, "plt": plt, "st": st, "px": px, "go": go,
            "libs_sni": libs_sni, "libs_baja": libs_baja, "libs_bridge": libs_bridge,
            "libs_gempa": libs_gempa, "libs_beton": libs_beton,
            "libs_hidrologi": libs_hidrologi, "libs_irigasi": libs_irigasi, 
            "libs_bendung": libs_bendung, "libs_jiat": libs_jiat,
            "libs_ahsp": libs_ahsp, "libs_rab_engine": libs_rab_engine,
            "libs_optimizer": libs_optimizer, "libs_research": libs_research,
            "libs_arch": libs_arch, "libs_zoning": libs_zoning, "libs_green": libs_green,
            "libs_pdf": libs_pdf, "libs_export": libs_export,
            "libs_bim_importer": libs_bim_importer
        }
        
        if has_geotek:
            library_kits['libs_geoteknik'] = libs_geoteknik
            library_kits['libs_pondasi'] = libs_pondasi
        if has_fem:
            library_kits['libs_fem'] = libs_fem
            
        local_vars.update(library_kits)
        
        if file_ifc_path: 
            local_vars["file_ifc_user"] = file_ifc_path
        
        exec(code_str, local_vars)
        
        for k, v in local_vars.items():
            if k not in library_kits and not k.startswith('__') and not isinstance(v, types.ModuleType):
                st.session_state.shared_execution_vars[k] = v     
        return True
    except Exception as e:
        # Error handling silent agar tidak mengganggu UX chat
        return False

def clean_text_for_report(text):
    """Membersihkan teks dari blok kode & artefak."""
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
            return libs_pdf.create_tabg_report(st.session_state, project_name="Proyek SmartBIM")
        except: pass
    
    # Fallback PDF Sederhana
    clean_content = clean_text_for_report(text_content)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 6, clean_content)
    return pdf.output(dest='S').encode('latin-1')

def create_slf_report_pdf(hasil_analisa, project_name="Proyek SLF"):
    """
    Generator PDF Khusus Laporan SLF Struktur (Audit Forensik).
    """
    pdf = FPDF()
    pdf.add_page()
    
    # HEADER
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "LAPORAN KAJIAN TEKNIS STRUKTUR (SLF)", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "Berdasarkan Standar SNI 2847:2019", 0, 1, 'C')
    pdf.line(10, 25, 200, 25)
    pdf.ln(10)
    
    # DETAIL PROYEK
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"PROYEK: {project_name}", 0, 1)
    
    # HASIL ANALISA
    pdf.set_font("Arial", '', 11)
    pdf.cell(50, 10, "Komponen", 1)
    pdf.cell(0, 10, f": {hasil_analisa.get('Komponen', 'Kolom Struktur')}", 1, 1)
    
    pdf.cell(50, 10, "Beban Rencana (Pu)", 1)
    pdf.cell(0, 10, f": {hasil_analisa.get('Beban_Rencana (kN)', 0)} kN", 1, 1)
    
    pdf.cell(50, 10, "Kapasitas Max", 1)
    pdf.cell(0, 10, f": {hasil_analisa.get('Kapasitas_Max (kN)', 0)} kN", 1, 1)
    
    pdf.cell(50, 10, "DCR Ratio", 1)
    pdf.cell(0, 10, f": {hasil_analisa.get('DCR_Ratio', 0)}", 1, 1)
    
    # Status Berwarna (Text Only di PDF sederhana)
    status = hasil_analisa.get('Status', 'UNKNOWN')
    pdf.cell(50, 10, "STATUS KEAMANAN", 1)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f": {status}", 1, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 6, "Catatan: Laporan ini dihasilkan secara otomatis oleh Enginex Ultimate System. Validasi akhir tetap diperlukan oleh Tenaga Ahli bersertifikat.")
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. SIDEBAR & NAVIGASI
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
    
    # --- NAVIGASI UTAMA ---
    st.markdown("### 🧭 Navigasi")
    app_mode = st.radio("Pilih Fitur:", [
        "💬 AI Assistant (Chat)",
        "🏗️ Audit Struktur (Forensik)",
        "🌪️ Analisis Gempa (SNI 1726)"
    ])
    st.divider()

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
        "models/gemini-robotics-er-1-preview",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-image",
        "gemini-2.5-flash-preview",
        "gemini-3-flash-preview",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
        "models/gemini-robotics-er-1-preview",
    ]
    model_name = st.selectbox("🧠 Model AI:", AVAILABLE_MODELS, index=0)
    
    # 3. SETTING PROYEK
    st.divider()
    projects = db.daftar_proyek()
    nama_proyek = st.selectbox("Proyek Aktif:", projects) if projects else st.text_input("Nama Proyek Baru:", "Proyek-01")
    
    if st.button("💾 Backup Data"):
        st.json(db.export_data())

    if st.button("🧹 Reset Session"):
        st.session_state.shared_execution_vars = {}
        st.session_state.processed_files.clear()
        st.rerun()

# ==========================================
# 5. KONTEN HALAMAN (BERDASARKAN MODE)
# ==========================================
st.title(f"📂 {nama_proyek}")

# ------------------------------------------
# MODE A: AI CHAT ASSISTANT
# ------------------------------------------
if app_mode == "💬 AI Assistant (Chat)":
    
    # Konfigurasi Ahli
    use_auto_pilot = st.checkbox("🤖 Auto-Pilot (Smart Router)", value=True)
    daftar_ahli = get_persona_list()
    
    if not use_auto_pilot:
        selected_expert = st.selectbox("👨‍💼 Pilih Spesialis:", daftar_ahli)
        st.session_state.current_expert_active = selected_expert
    else:
        st.caption(f"Ahli Aktif: {st.session_state.current_expert_active}")

    # History Chat
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
                    with st.expander("🛠️ Lihat Detail Teknis (Engine Output)"):
                        st.code(code_content, language='python')
                        st.download_button("📥 Download Script (.py)", code_content, f"script_{download_btn_counter}.py", key=f"dl_{download_btn_counter}")
                    execute_generated_code(code_content)
                else:
                    st.markdown(part)

    # Input User
    prompt = st.chat_input("Ketik perintah desain, hitungan, atau analisa...")
    if prompt:
        # 1. Routing Ahli
        target_expert = st.session_state.current_expert_active
        if use_auto_pilot:
            try:
                router = genai.GenerativeModel("gemini-1.5-flash")
                res = router.generate_content(f"Pertanyaan: '{prompt}'. Pilih satu ahli paling cocok dari: {daftar_ahli}. Jawab Nama Saja.")
                sug = res.text.strip()
                if any(sug in a for a in daftar_ahli): target_expert = sug; st.session_state.current_expert_active = sug
            except: pass

        # 2. Simpan & Tampilkan User Chat
        db.simpan_chat(nama_proyek, target_expert, "user", prompt)
        with st.chat_message("user"): st.markdown(prompt)

        # 3. Proses AI
        full_prompt = [prompt]
        file_ifc_path = None
        
        # Handle Uploads
        uploaded_files = st.file_uploader("Upload Data Tambahan", type=["png","jpg","pdf","ifc"], label_visibility="collapsed")
        if uploaded_files:
             # (Logika upload file sama seperti sebelumnya, disederhanakan di sini)
             pass

        with st.chat_message("assistant"):
            with st.spinner(f"{target_expert} sedang bekerja..."):
                try:
                    persona_instr = gems_persona.get(target_expert, gems_persona["👑 The GEMS Grandmaster"])
                    SYS = persona_instr + "\n[ATURAN]: Gunakan Plotly untuk grafik. Output kode Python lengkap."
                    
                    model = genai.GenerativeModel(model_name, system_instruction=SYS)
                    chat = model.start_chat(history=[{"role": "user" if h['role']=="user" else "model", "parts": [h['content']]} for h in history])
                    response = chat.send_message(full_prompt)
                    
                    # Tampilkan & Eksekusi
                    st.markdown(response.text) # Sederhana: Tampilkan semua dulu
                    
                    # Cek kode untuk dieksekusi background (agar grafik muncul)
                    parts = re.split(r"(```python.*?```)", response.text, flags=re.DOTALL)
                    for part in parts:
                        if part.startswith("```python"):
                            code = part.replace("```python", "").replace("```", "").strip()
                            execute_generated_code(code)

                    db.simpan_chat(nama_proyek, target_expert, "assistant", response.text)
                    
                    # Export Buttons
                    c1, c2, c3 = st.columns(3)
                    if c1.button("📄 Buat PDF"): pass # Placeholder logic
                    
                except Exception as e:
                    st.error(f"Error AI: {e}")

# ------------------------------------------
# MODE B: AUDIT STRUKTUR FORENSIK (MANUAL TOOL)
# ------------------------------------------
elif app_mode == "🏗️ Audit Struktur (Forensik)":
    
    st.markdown("## 🏗️ Audit Forensik Struktur (Beton Bertulang)")
    st.info("Modul ini melakukan pengecekan kapasitas kolom berdasarkan SNI 2847:2019 menggunakan Diagram Interaksi P-M.")

    # 1. INPUT PARAMETER
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("🧱 Material")
            fc_input = st.number_input("Mutu Beton (fc') [MPa]", value=25.0, step=5.0)
            fy_input = st.number_input("Mutu Baja (fy) [MPa]", value=420.0, step=10.0)
        with c2:
            st.subheader("📐 Geometri")
            b_input = st.number_input("Lebar (b) [mm]", value=400.0, step=50.0)
            h_input = st.number_input("Tinggi (h) [mm]", value=400.0, step=50.0)
        with c3:
            st.subheader("⛓️ Tulangan")
            D_tul = st.number_input("Diameter (D) [mm]", value=16.0, step=1.0)
            n_tul = st.number_input("Jumlah Batang", value=8, step=2)

    st.markdown("---")
    st.subheader("⬇️ Beban Rencana (Load Effect)")
    cl1, cl2 = st.columns(2)
    Pu_user = cl1.number_input("Gaya Aksial Terfaktor (Pu) [kN]", value=800.0)
    Mu_user = cl2.number_input("Momen Lentur Terfaktor (Mu) [kNm]", value=150.0)

    # 2. EKSEKUSI HITUNGAN
    if st.button("🚀 MULAI AUDIT FORENSIK", type="primary"):
        try:
            # Hitung Ast
            Ast_input = n_tul * 0.25 * 3.14159 * (D_tul ** 2)
            
            # Panggil Library Beton
            hasil_analisa = libs_beton.SNIBeton2019.analyze_column_capacity(
                b_input, h_input, fc_input, fy_input, Ast_input, Pu_user, Mu_user
            )
            
            # Generate Diagram Interaksi
            pm_data = libs_beton.SNIBeton2019.generate_interaction_diagram(
                b_input, h_input, fc_input, fy_input, Ast_input
            )

            # 3. VISUALISASI HASIL
            st.divider()
            
            # A. Scorecard
            m1, m2, m3 = st.columns(3)
            status_text = hasil_analisa['Status']
            color_metric = "normal" if "AMAN" in status_text else "inverse"
            
            m1.metric("Status Keamanan", status_text, delta_color=color_metric)
            m2.metric("DCR Ratio", f"{hasil_analisa['DCR_Ratio']} x", "Batas < 1.0")
            m3.metric("Kapasitas Aksial", f"{hasil_analisa['Kapasitas_Max (kN)']} kN")

            # B. Plotly Chart
            df_plot = pm_data['Plot_Data']
            fig = go.Figure()
            
            # Area Kapasitas
            fig.add_trace(go.Scatter(
                x=df_plot['M_Capacity'], y=df_plot['P_Capacity'], 
                fill='toself', fillcolor='rgba(0, 200, 83, 0.2)',
                line=dict(color='green', width=2),
                name='Zona Aman (Phi Pn-Mn)'
            ))
            
            # Titik Beban
            pt_color = 'blue' if "AMAN" in status_text else 'red'
            fig.add_trace(go.Scatter(
                x=[Mu_user], y=[Pu_user],
                mode='markers+text',
                marker=dict(color=pt_color, size=15, symbol='x'),
                name='Beban (Pu, Mu)',
                text=[f"DCR: {hasil_analisa['DCR_Ratio']}"],
                textposition="top right"
            ))
            
            fig.update_layout(
                title="Diagram Interaksi P-M (Audit Column)",
                xaxis_title="Momen (kNm)", yaxis_title="Aksial (kN)",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # C. Download Report
            pdf_bytes = create_slf_report_pdf(hasil_analisa, project_name=nama_proyek)
            st.download_button(
                label="📄 DOWNLOAD LAPORAN RESMI SLF (PDF)",
                data=pdf_bytes,
                file_name=f"Audit_SLF_{nama_proyek}.pdf",
                mime="application/pdf"
            )
            
        except Exception as e:
            st.error(f"Terjadi kesalahan perhitungan: {e}")
            st.warning("Pastikan modul 'libs_beton.py' sudah benar dan tersedia.")

# ------------------------------------------
# MODE C: ANALISIS GEMPA (FULL OPENSEES)
# ------------------------------------------
elif app_mode == "🌪️ Analisis Gempa (SNI 1726)":
    st.header("🌪️ Analisis Modal Respon Spektrum (OpenSees Engine)")
    st.info("Fitur ini menggunakan Finite Element Method (FEM) untuk menghitung karakteristik dinamis bangunan sesuai SNI 1726:2019.")

    if not has_fem:
        st.error("⚠️ Library `openseespy` belum terdeteksi/terinstall. Fitur ini dinonaktifkan.")
        st.stop()

    with st.expander("⚙️ Konfigurasi Model Struktur", expanded=True):
        c1, c2, c3 = st.columns(3)
        jml_lantai = c1.number_input("Jumlah Lantai", 1, 20, 5)
        tinggi_lantai = c1.number_input("Tinggi Antar Lantai (m)", 2.5, 6.0, 3.5)
        
        bentang_x = c2.number_input("Bentang Arah X (m)", 3.0, 12.0, 6.0)
        bentang_y = c2.number_input("Bentang Arah Y (m)", 3.0, 12.0, 6.0)
        
        fc_mutu = c3.number_input("Mutu Beton (MPa)", 20, 60, 30)
    
    if st.button("🚀 RUN ANALISIS FEM (OpenSees)"):
        with st.spinner("Memproses Matriks Kekakuan & Eigenvalue..."):
            try:
                # 1. Inisialisasi Engine
                engine = libs_fem.OpenSeesEngine()
                
                # 2. Build Model
                engine.build_simple_portal(bentang_x, bentang_y, tinggi_lantai, jml_lantai, fc_mutu)
                
                # 3. Run Analysis
                df_modal = engine.run_modal_analysis(num_modes=3)
                
                st.success("Analisis Selesai!")
                
                # 4. Tampilkan Hasil
                st.subheader("📊 Hasil Modal Analysis (Mode Shapes)")
                st.dataframe(df_modal, use_container_width=True)
                
                # 5. Interpretasi Engineer
                t1 = df_modal.iloc[0]['Period (T) [detik]']
                st.markdown(f"""
                **Interpretasi Teknis:**
                * **Perioda Alami Fundamental (T1):** `{t1} detik`
                * Jika T1 > batas izin SNI ($C_u . T_a$), struktur mungkin terlalu fleksibel (Lentur).
                * Jika T1 terlalu kecil, struktur sangat kaku.
                """)
                
                # [Visualisasi Sederhana Mode Shape nanti bisa ditambahkan disini pakai Plotly]
                
            except Exception as e:
                st.error(f"Terjadi Kesalahan pada Engine FEM: {e}")
                st.caption("Pastikan library 'openseespy' sudah terinstall di server.")

# ==========================================
# FOOTER
# ==========================================
st.markdown("---")
st.caption("© 2025 ENGINEX Ultimate System | Powered by Gemini 1.5 & Streamlit")
