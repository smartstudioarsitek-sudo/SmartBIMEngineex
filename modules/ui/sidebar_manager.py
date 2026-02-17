# modules/ui/sidebar_manager.py
import streamlit as st
import os
import json
from core.persona import get_persona_list

def render_sidebar(db_backend):
    """
    Mengurus Tampilan Sidebar: API Key, Menu, dan Save/Load Project JSON.
    """
    config = {}
    
    with st.sidebar:
        st.title("🛡️ ENGINEX GOV.VER")
        st.caption("Enterprise Modular Edition")
        
        # --- 1. LOGIKA API KEY (LEBIH TEGAS) ---
        # Prioritas 1: Secrets (Cloud)
        if "GOOGLE_API_KEY" in st.secrets:
            config['api_key'] = st.secrets["GOOGLE_API_KEY"]
            st.success("🔒 API Key: Terdeteksi (Cloud Secrets)")
        
        # Prioritas 2: Environment Variable (Lokal)
        elif os.environ.get("GOOGLE_API_KEY"):
            config['api_key'] = os.environ.get("GOOGLE_API_KEY")
            st.success("🔒 API Key: Terdeteksi (Environment)")
            
        # Prioritas 3: Input Manual (Kalau 1 & 2 Gagal)
        else:
            st.warning("⚠️ Mode Manual (Tidak Aman)")
            config['api_key'] = st.text_input("🔑 Masukkan Google API Key:", type="password")
            if not config['api_key']:
                st.stop() # Stop aplikasi kalau tidak ada kunci

        st.divider()
        
        # --- 2. MENU NAVIGASI ---
        config['menu'] = st.radio(
            "Pilih Modul:", 
            ["🤖 AI Assistant", "🌪️ Analisis Gempa (FEM)", "🏗️ Audit Struktur"]
        )
        
        st.divider()
        
        # --- 3. FITUR SAVE / OPEN PROJECT (YANG HILANG KEMARIN) ---
        with st.expander("💾 Manajemen Data Proyek", expanded=False):
            st.caption("Simpan/Buka Pekerjaan (Format JSON)")
            
            # A. SAVE PROJECT (Download JSON)
            # Kita ambil history chat dari backend untuk disimpan
            # (Bisa ditambah data form struktur jika perlu)
            project_data = {
                "chat_history": db_backend.get_all_history_raw(), # Asumsi ada fungsi ini atau kita ambil manual
                "project_name": st.session_state.get('active_project', 'Default'),
                "form_beton": st.session_state.get('form_beton', {})
            }
            json_str = json.dumps(project_data, indent=2)
            
            st.download_button(
                label="📥 Save Project (JSON)",
                data=json_str,
                file_name="enginex_project_backup.json",
                mime="application/json"
            )
            
            # B. OPEN PROJECT (Upload JSON)
            uploaded_json = st.file_uploader("📂 Open Project (JSON)", type=["json"])
            if uploaded_json is not None:
                if st.button("Load Data JSON"):
                    try:
                        data = json.load(uploaded_json)
                        # Restore Form Beton
                        if 'form_beton' in data:
                            st.session_state.form_beton = data['form_beton']
                        # Restore Project Name
                        if 'project_name' in data:
                            st.session_state.active_project = data['project_name']
                        
                        st.success("✅ Data Proyek Berhasil Diload!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal baca file: {e}")

        st.divider()

        # --- 4. KONFIGURASI SPESIFIK MENU ---
        if config['menu'] == "🤖 AI Assistant":
            st.markdown("### 🧠 Konfigurasi AI")
            config['model_type'] = st.selectbox("Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
            
            use_pilot = st.checkbox("🤖 Auto-Pilot", value=True)
            config['auto_pilot'] = use_pilot
            if not use_pilot:
                config['persona'] = st.selectbox("Ahli:", get_persona_list())
            else:
                config['persona'] = "👑 The GEMS Grandmaster"
            
            # File Upload untuk Chat
            st.markdown("### 📎 Data Pendukung")
            config['files'] = st.file_uploader("Upload Dokumen/Gambar", accept_multiple_files=True)
            
            if st.button("🧹 Hapus Chat"):
                config['reset_trigger'] = True

    return config
