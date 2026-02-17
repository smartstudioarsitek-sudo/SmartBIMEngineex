# modules/ui/sidebar_manager.py
import streamlit as st
import os
import json
from core.persona import get_persona_list

def render_sidebar(db_backend):
    """
    Versi SAFE MODE: Menghapus panggilan fungsi yang menyebabkan crash.
    """
    config = {}
    
    with st.sidebar:
        st.title("🛡️ ENGINEX GOV.VER")
        st.caption("Enterprise Modular Edition")
        
        # --- 1. API KEY ---
        if "GOOGLE_API_KEY" in st.secrets:
            config['api_key'] = st.secrets["GOOGLE_API_KEY"]
            st.success("🔒 API Key: Terdeteksi (Cloud)")
        elif os.environ.get("GOOGLE_API_KEY"):
            config['api_key'] = os.environ.get("GOOGLE_API_KEY")
            st.success("🔒 API Key: Terdeteksi (Env)")
        else:
            st.warning("⚠️ Mode Manual")
            config['api_key'] = st.text_input("🔑 Masukkan Google API Key:", type="password")
            if not config['api_key']:
                st.stop()

        st.divider()
        
        # --- 2. MENU ---
        config['menu'] = st.radio(
            "Pilih Modul:", 
            ["🤖 AI Assistant", "🌪️ Analisis Gempa (FEM)", "🏗️ Audit Struktur"]
        )
        
        st.divider()
        
        # --- 3. MANAJEMEN DATA (DIPERBAIKI) ---
        # Bagian ini yang tadi bikin CRASH. Sekarang kita buat lebih sederhana & aman.
        with st.expander("💾 Manajemen Data Proyek", expanded=False):
            st.caption("Simpan/Buka Pekerjaan (JSON)")
            
            # Kita hanya simpan data form dan nama proyek dulu (Anti-Crash)
            project_data = {
                "project_name": st.session_state.get('active_project', 'Default'),
                "form_beton": st.session_state.get('form_beton', {}),
                "timestamp": str(pd.Timestamp.now()) if 'pd' in globals() else ""
            }
            json_str = json.dumps(project_data, indent=2)
            
            st.download_button(
                label="📥 Save Data Struktur (JSON)",
                data=json_str,
                file_name="project_backup.json",
                mime="application/json"
            )
            
            # Upload
            uploaded_json = st.file_uploader("📂 Load Data", type=["json"])
            if uploaded_json is not None:
                if st.button("Load Data JSON"):
                    try:
                        data = json.load(uploaded_json)
                        if 'form_beton' in data:
                            st.session_state.form_beton = data['form_beton']
                            st.success("✅ Data Form Berhasil Diload!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Gagal: {e}")

        st.divider()

        # --- 4. KONFIGURASI MENU ---
        if config['menu'] == "🤖 AI Assistant":
            config['model_type'] = st.selectbox("Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])
            
            use_pilot = st.checkbox("🤖 Auto-Pilot", value=True)
            config['auto_pilot'] = use_pilot
            if not use_pilot:
                config['persona'] = st.selectbox("Ahli:", get_persona_list())
            else:
                config['persona'] = "👑 The GEMS Grandmaster"
            
            config['files'] = st.file_uploader("Upload Dokumen", accept_multiple_files=True)
            
            # Fitur Open/Save Project Database
            st.markdown("### 📂 Proyek (CDE)")
            projects = db_backend.daftar_proyek()
            mode_proj = st.radio("Mode:", ["Buka", "Baru"], horizontal=True, label_visibility="collapsed")
            
            if mode_proj == "Baru":
                new_p = st.text_input("Nama Proyek Baru:")
                if st.button("Buat Proyek"):
                    if new_p:
                        config['new_project_trigger'] = new_p
                        config['active_project'] = new_p
            else:
                config['active_project'] = st.selectbox("Pilih Proyek:", projects) if projects else "Default Project"
                
            if st.button("🧹 Hapus Chat"):
                config['reset_trigger'] = True
        else:
            # Default project name untuk menu lain
            config['active_project'] = "Default Project"

    return config
