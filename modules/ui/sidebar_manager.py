# modules/ui/sidebar_manager.py
import streamlit as st
import os
from core.persona import get_persona_list

def render_sidebar(db_backend):
    """
    Menangani Sidebar: API Key, Menu, dan Project Management.
    """
    config = {}
    
    with st.sidebar:
        st.title("🛡️ ENGINEX GOV.VER")
        st.caption("Enterprise Modular Edition")
        
        # --- 1. KEAMANAN API KEY (PERBAIKAN LOGIKA) ---
        # Cek berbagai kemungkinan nama key di secrets
        api_secret = None
        if "GOOGLE_API_KEY" in st.secrets:
            api_secret = st.secrets["GOOGLE_API_KEY"]
        elif "api_key" in st.secrets:
            api_secret = st.secrets["api_key"]
            
        if api_secret:
            config['api_key'] = api_secret
            st.success("🔒 API Key Terdeteksi (Secure Mode)")
        else:
            # Fallback ke Environment Variable
            env_key = os.environ.get("GOOGLE_API_KEY")
            if env_key:
                config['api_key'] = env_key
                st.success("🔒 API Key dari Environment")
            else:
                st.warning("⚠️ Mode Publik (Manual Input)")
                config['api_key'] = st.text_input("🔑 Masukkan API Key:", type="password")
                if not config['api_key']:
                    st.stop() # Hentikan app jika tidak ada key
        
        st.divider()
        
        # --- 2. NAVIGASI MENU ---
        config['menu'] = st.radio(
            "Pilih Modul:", 
            ["🤖 AI Assistant", "🌪️ Analisis Gempa (FEM)", "🏗️ Audit Struktur"]
        )
        
        st.divider()
        
        # --- 3. KONFIGURASI SESUAI MENU ---
        
        # A. Konfigurasi AI (Hanya muncul di menu AI)
        if config['menu'] == "🤖 AI Assistant":
            with st.expander("🧠 Konfigurasi Model", expanded=True):
                config['model_type'] = st.selectbox(
                    "Versi Model:", 
                    ["gemini-1.5-flash", "gemini-1.5-pro"],
                    index=0
                )
                
                use_pilot = st.checkbox("🤖 Auto-Pilot Mode", value=True)
                config['auto_pilot'] = use_pilot
                if not use_pilot:
                    config['persona'] = st.selectbox("Pilih Ahli:", get_persona_list())
                else:
                    config['persona'] = "👑 The GEMS Grandmaster"

            # B. Project Management (Fitur Open/Save/New)
            st.markdown("### 📂 Proyek (CDE)")
            projects = db_backend.daftar_proyek()
            
            mode_proj = st.radio("Mode:", ["Buka Proyek", "Buat Baru"], horizontal=True, label_visibility="collapsed")
            
            if mode_proj == "Buat Baru":
                new_p = st.text_input("Nama Proyek Baru:", placeholder="Cth: GEDUNG-A")
                if st.button("💾 Buat & Simpan"):
                    if new_p:
                        config['new_project_trigger'] = new_p
                        config['active_project'] = new_p
                    else:
                        st.error("Nama tidak boleh kosong")
            else:
                # Ini fungsi "OPEN PROJECT"
                if projects:
                    config['active_project'] = st.selectbox("Pilih Proyek:", projects)
                else:
                    st.info("Belum ada proyek.")
                    config['active_project'] = "Default Project"
                    
            # C. File Upload
            st.markdown("### 📎 Data Pendukung")
            config['files'] = st.file_uploader("Upload", accept_multiple_files=True, label_visibility="collapsed")
            
            if st.button("🧹 Reset Chat History"):
                config['reset_trigger'] = True

    return config
