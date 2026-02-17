# modules/ui/sidebar_manager.py
import streamlit as st
import os
from core.persona import get_persona_list

def render_sidebar(db_backend):
    """
    Menangani semua tampilan Sidebar: API Key, Menu, Model Selector, Project.
    Mengembalikan dictionary 'config' yang berisi semua pilihan user.
    """
    config = {}
    
    with st.sidebar:
        st.title("🛡️ ENGINEX GOV.VER")
        st.caption("Enterprise Modular Edition")
        
        # 1. SECURITY & API KEY
        if 'api_key' in st.secrets:
            config['api_key'] = st.secrets['api_key'] # Atau GOOGLE_API_KEY
            st.success("🔒 Secure Mode (Secrets)")
        else:
            config['api_key'] = st.text_input("🔑 API Key:", type="password")
            if not config['api_key']:
                st.warning("Input API Key untuk lanjut.")
                st.stop()
        
        st.divider()
        
        # 2. NAVIGASI UTAMA
        config['menu'] = st.radio(
            "Pilih Modul:", 
            ["🤖 AI Assistant", "🌪️ Analisis Gempa (FEM)", "🏗️ Audit Struktur"]
        )
        
        st.divider()
        
        # 3. SETTING KHUSUS AI (Ini yang kemarin sempat hilang)
        if config['menu'] == "🤖 AI Assistant":
            st.markdown("### 🧠 Konfigurasi AI")
            config['model_type'] = st.selectbox(
                "Versi Model:", 
                ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
                index=0,
                help="Flash untuk cepat, Pro untuk analisis mendalam."
            )
            
            # Persona
            st.markdown("### 🎭 Persona")
            use_pilot = st.checkbox("🤖 Auto-Pilot Mode", value=True)
            config['auto_pilot'] = use_pilot
            if not use_pilot:
                config['persona'] = st.selectbox("Pilih Ahli:", get_persona_list())
            else:
                config['persona'] = "👑 The GEMS Grandmaster"

            # Project Management (ISO 19650)
            st.markdown("### 📂 Proyek (CDE)")
            projects = db_backend.daftar_proyek()
            mode_proj = st.radio("Opsi:", ["Buka", "Baru"], horizontal=True, label_visibility="collapsed")
            
            if mode_proj == "Baru":
                new_p = st.text_input("Nama Proyek Baru:")
                if st.button("Buat Folder CDE"):
                    config['new_project_trigger'] = new_p
                config['active_project'] = new_p
            else:
                config['active_project'] = st.selectbox("Pilih:", projects) if projects else "Default"
                
            # File Upload
            st.markdown("### 📎 Data Pendukung")
            config['files'] = st.file_uploader("Upload", accept_multiple_files=True, label_visibility="collapsed")
            
            if st.button("🧹 Reset Chat"):
                config['reset_trigger'] = True

    return config