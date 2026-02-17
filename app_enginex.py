import streamlit as st
import google.generativeai as genai
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go # Wajib ada untuk grafik P-M
import plotly.express as px       # Wajib ada untuk grafik Gempa
import json
from PIL import Image
import PyPDF2

# --- 1. IMPORT MODULES (Pastikan path benar) ---
try:
    from core.backend_enginex import EnginexBackend
    from modules.ui.sidebar_manager import render_sidebar
    from modules.utils.reporter import export_dataframe_to_excel, create_pdf_report
    from modules.utils.pdf_extractor import extract_text_from_pdf, ai_parse_structural_data
    
    # Engineering Modules
    from modules.struktur.validator_sni import cek_dimensi_kolom, cek_rasio_tulangan
    from modules.struktur.peta_gempa_indo import get_data_kota, hitung_respon_spektrum
    
    # Safe Import untuk modul berat
    try:
        from modules.struktur import libs_fem 
        from modules.struktur import libs_beton
    except ImportError: pass

except ImportError as e:
    st.error(f"⚠️ Gagal memuat modul dependencies: {e}")
    st.stop()

# --- 2. SETUP APP ---
st.set_page_config(page_title="ENGINEX Ultimate", page_icon="🏗️", layout="wide")

# Init Backend
if 'backend' not in st.session_state: st.session_state.backend = EnginexBackend()
db = st.session_state.backend

# Init Session State untuk Form (Agar input tidak hilang saat ganti tab)
if 'form_beton' not in st.session_state:
    st.session_state.form_beton = {
        'fc': 25.0, 'fy': 420.0, 'b': 400.0, 'h': 400.0, 
        'd_tul': 16.0, 'n_tul': 8, 'pu': 800.0, 'mu': 150.0
    }

# --- 3. RENDER SIDEBAR (Panggil Modul UI yang sudah diperbaiki) ---
cfg = render_sidebar(db)

# Config AI
if cfg.get('api_key'):
    genai.configure(api_key=cfg['api_key'])

# Handle Project Creation
if cfg.get('new_project_trigger'):
    st.toast(f"✅ Proyek {cfg['new_project_trigger']} berhasil dibuat!")

# Handle Reset
if cfg.get('reset_trigger'):
    db.clear_chat(cfg['active_project'], cfg.get('persona', 'User'))
    st.rerun()


# ==========================================
# 4. ROUTING MENU UTAMA
# ==========================================

# --- A. MENU AI ASSISTANT ---
if cfg['menu'] == "🤖 AI Assistant":
    st.header(f"🤖 AI Assistant ({cfg.get('model_type', 'Standard')})")
    st.caption(f"Proyek Aktif: {cfg.get('active_project', 'Default')}")
    
    active_persona = cfg.get('persona', "General")
    history = db.get_chat_history(cfg.get('active_project', 'Default'), active_persona)
    
    # Render Chat
    for msg in history:
        with st.chat_message(msg['role']): st.markdown(msg['content'])
        
    # Input User
    prompt = st.chat_input("Ketik perintah...")
    if prompt:
        with st.chat_message("user"): st.markdown(prompt)
        db.simpan_chat(cfg['active_project'], active_persona, "user", prompt)
        
        # Siapkan Konteks File
        full_prompt = [prompt]
        if cfg.get('files'):
            for f in cfg['files']:
                if f.type == "application/pdf":
                    txt = extract_text_from_pdf(f)
                    full_prompt.append(f"Isi PDF {f.name}:\n{txt}")
                elif f.type.startswith("image"):
                    full_prompt.append(Image.open(f))
        
        # Panggil Gemini
        with st.chat_message("assistant"):
            with st.spinner("Berpikir..."):
                try:
                    # System Instruction untuk respon lebih bagus
                    sys_instr = "Anda adalah Ahli Teknik Sipil Senior. Gunakan Bahasa Indonesia Formal."
                    model = genai.GenerativeModel(cfg['model_type'], system_instruction=sys_instr)
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    db.simpan_chat(cfg['active_project'], active_persona, "assistant", response.text)
                except Exception as e:
                    st.error(f"Error AI: {e}")


# --- B. MENU FEM (GEMPA) ---
elif cfg['menu'] == "🌪️ Analisis Gempa (FEM)":
    st.header("🌪️ Analisis Gempa Dinamis (FEM)")
    
    # 1. Peta Gempa (Fitur Peta Kembali)
    with st.expander("🌍 Data Gempa (SNI 1726:2019)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            db_kota = get_data_kota()
            kota = st.selectbox("Lokasi Proyek", list(db_kota.keys()), index=8)
            data_g = db_kota[kota]
            
            # Logic disable input jika pilih kota otomatis
            is_manual = (kota == "Pilih Manual")
            ss = st.number_input("Ss (Short Period)", value=data_g['Ss'], disabled=not is_manual, format="%.2f")
            s1 = st.number_input("S1 (1-Sec Period)", value=data_g['S1'], disabled=not is_manual, format="%.2f")
        with c2:
            situs = st.selectbox("Kelas Situs Tanah", ["SA (Batuan Keras)", "SB (Batuan)", "SC (Tanah Keras)", "SD (Tanah Sedang)", "SE (Tanah Lunak)"])
            kode_situs = situs.split()[0]
            
            # Hitung Otomatis
            res_gempa = hitung_respon_spektrum(ss, s1, kode_situs)
            st.info(f"📊 **Parameter Desain:**\nSDS = {res_gempa['SDS']:.3f} g\nSD1 = {res_gempa['SD1']:.3f} g")

    # 2. Input Struktur
    st.divider()
    st.subheader("🏗️ Geometri Portal")
    col_g1, col_g2 = st.columns(2)
    lantai = col_g1.number_input("Jumlah Lantai", 1, 50, 5)
    tinggi = col_g1.number_input("Tinggi Tingkat (m)", 2.0, 6.0, 3.5)
    bx = col_g2.number_input("Bentang X (m)", 3.0, 12.0, 6.0)
    by = col_g2.number_input("Bentang Y (m)", 3.0, 12.0, 6.0)
    fc = st.number_input("Mutu Beton (MPa)", 20, 60, 30)

    # 3. Eksekusi & Grafik (Dikembalikan)
    if st.button("🚀 Run Analysis", type="primary"):
        if 'libs_fem' in sys.modules:
            with st.spinner("Running OpenSees Engine..."):
                try:
                    engine = libs_fem.OpenSeesEngine()
                    # Kirim parameter ke engine
                    engine.build_simple_portal(bx, by, tinggi, lantai, fc)
                    df_res = engine.run_modal_analysis()
                    
                    st.success("✅ Analisis Selesai!")
                    
                    # Tampilkan Grafik Respon Spektrum (RESTORED)
                    st.subheader("📈 Kurva Respon Spektrum")
                    T_vals = np.linspace(0, 4, 100)
                    Sa_vals = []
                    for t in T_vals:
                        if t < res_gempa['T0']: val = res_gempa['SDS'] * (0.4 + 0.6*t/res_gempa['T0'])
                        elif t < res_gempa['Ts']: val = res_gempa['SDS']
                        else: val = res_gempa['SD1'] / t
                        Sa_vals.append(val)
                    
                    fig_rsa = px.line(x=T_vals, y=Sa_vals, title=f"Respon Spektrum ({kota} - {kode_situs})")
                    st.plotly_chart(fig_rsa, use_container_width=True)

                    # Tampilkan Tabel & Grafik Batang (RESTORED)
                    st.subheader("📊 Mode Shapes")
                    c_res1, c_res2 = st.columns([1, 2])
                    c_res1.dataframe(df_res, use_container_width=True)
                    
                    fig_bar = px.bar(df_res, x='Mode', y='Period (T) [detik]', title="Perioda Alami Struktur")
                    c_res2.plotly_chart(fig_bar, use_container_width=True)
                    
                    # Tombol Download (RESTORED)
                    st.divider()
                    xls = export_dataframe_to_excel(df_res)
                    st.download_button("📥 Download Laporan Excel", xls, "Hasil_Gempa.xlsx")
                    
                except Exception as e:
                    st.error(f"Error Engine: {e}")
        else:
            st.warning("⚠️ Engine FEM tidak tersedia.")


# --- C. MENU AUDIT STRUKTUR ---
elif cfg['menu'] == "🏗️ Audit Struktur":
    st.header("🏗️ Audit Forensik Struktur")
    
    # 1. PDF Auto-Fill (Tetap Ada)
    with st.expander("📂 Import Data dari Laporan (PDF)"):
        f_pdf = st.file_uploader("Upload Laporan", type="pdf")
        if f_pdf and st.button("🤖 Ekstrak Data Otomatis"):
            with st.spinner("Menganalisa Dokumen..."):
                txt = extract_text_from_pdf(f_pdf)
                # Gunakan API key dari config sidebar
                if cfg.get('api_key'):
                    data = ai_parse_structural_data(txt, cfg['api_key'])
                    if data:
                        st.session_state.form_beton.update(data)
                        st.success("✅ Formulir terisi otomatis dari PDF!")
                        st.rerun()
                else:
                    st.error("API Key diperlukan untuk fitur AI ini.")

    # 2. Form Input Lengkap (RESTORED SEMUA FIELD)
    st.divider()
    with st.container(border=True):
        st.subheader("⚙️ Parameter Struktur")
        c1, c2, c3 = st.columns(3)
        
        # Menggunakan Session State agar nilai tidak hilang
        fc = c1.number_input("Mutu Beton (fc')", value=st.session_state.form_beton['fc'])
        fy = c1.number_input("Mutu Baja (fy)", value=st.session_state.form_beton['fy'])
        
        b = c2.number_input("Lebar (b)", value=st.session_state.form_beton['b'])
        h = c2.number_input("Tinggi (h)", value=st.session_state.form_beton['h'])
        
        d_tul = c3.number_input("Diameter Tulangan", value=st.session_state.form_beton['d_tul'])
        n_tul = c3.number_input("Jumlah Batang", value=int(st.session_state.form_beton['n_tul']))
        
        st.markdown("---")
        col_load1, col_load2 = st.columns(2)
        pu = col_load1.number_input("Beban Aksial (Pu) [kN]", value=st.session_state.form_beton['pu'])
        mu = col_load2.number_input("Momen Lentur (Mu) [kNm]", value=st.session_state.form_beton['mu'])
        
        # Update Session State
        st.session_state.form_beton.update({'fc': fc, 'fy': fy, 'b': b, 'h': h, 'd_tul': d_tul, 'n_tul': n_tul, 'pu': pu, 'mu': mu})

    # 3. Validasi & Hitung (RESTORED)
    if st.button("🚀 Cek SNI & Hitung Kapasitas", type="primary"):
        # Pre-Audit Check
        errs = cek_dimensi_kolom(b, h, 5)
        err_tul, rho = cek_rasio_tulangan(b, h, n_tul, d_tul)
        
        # Tampilkan Error/Warning
        lolos = True
        if errs:
            for e in errs: 
                if "GAGAL" in e: st.error(e); lolos=False
                else: st.warning(e)
        if err_tul:
            for e in err_tul: 
                if "GAGAL" in e: st.error(e); lolos=False
                else: st.warning(e)

        if lolos:
            if 'libs_beton' in sys.modules:
                from modules.struktur.libs_beton import SNIBeton2019
                
                ast = n_tul * 0.25 * 3.14159 * (d_tul ** 2)
                hasil = SNIBeton2019.analyze_column_capacity(b, h, fc, fy, ast, pu, mu)
                pm_data = SNIBeton2019.generate_interaction_diagram(b, h, fc, fy, ast)
                
                # Visualisasi Hasil (RESTORED)
                st.subheader("📊 Hasil Analisa")
                m1, m2, m3 = st.columns(3)
                status_aman = hasil['Status']
                color = "normal" if "AMAN" in status_aman else "inverse"
                
                m1.metric("Status", status_aman, delta="SAFE" if "AMAN" in status_aman else "UNSAFE", delta_color=color)
                m2.metric("DCR Ratio", f"{hasil['DCR_Ratio']} x")
                m3.metric("Kapasitas Max", f"{hasil['Kapasitas_Max (kN)']} kN")
                
                # Plot P-M Diagram (RESTORED PLOTLY)
                df_plot = pm_data['Plot_Data']
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_plot['M_Capacity'], y=df_plot['P_Capacity'], fill='toself', name='Kapasitas Aman', line=dict(color='#2ecc71')))
                fig.add_trace(go.Scatter(x=[mu], y=[pu], mode='markers+text', marker=dict(size=12, color='red', symbol='x'), name='Beban', text=["Beban"], textposition="top right"))
                
                fig.update_layout(title="Diagram Interaksi P-M (SNI 2847)", xaxis_title="Momen (kNm)", yaxis_title="Aksial (kN)", height=500)
                st.plotly_chart(fig, use_container_width=True)
                
                # Export Button (RESTORED)
                st.divider()
                pdf_bytes = create_pdf_report("Laporan Audit Struktur", {
                    "Dimensi": f"{b} x {h} mm",
                    "Tulangan": f"{n_tul} D{d_tul}",
                    "Status": status_aman,
                    "DCR": hasil['DCR_Ratio']
                })
                st.download_button("📄 Download Laporan PDF", pdf_bytes, "Audit_Report.pdf")
            else:
                st.warning("Library Beton tidak tersedia.")
