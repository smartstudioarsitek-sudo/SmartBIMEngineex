import streamlit as st
import google.generativeai as genai
from modules.utils import libs_pdf
from modules.utils import prompt_registry

def get_working_model(system_instruction):
    """
    [FITUR BARU] AUTO-FALLBACK MODEL
    Mencari versi model Gemini yang paling kompatibel dan tidak error.
    """
    models_to_try = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash",
        "gemini-pro" # Fallback terakhir jika API Key versi lama
    ]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            # Uji coba instansiasi (jika gagal akan lari ke except)
            return model, model_name
        except:
            continue
            
    raise Exception("Tidak ada versi Gemini yang kompatibel dengan API Key Anda.")

def render_auto_chain_panel(module_category, persona_name):
    """
    Panel Generator Laporan Universal (Sistem Step-by-Step / Next-Next)
    """
    st.markdown("---")
    st.subheader(f"🚀 Generator Dokumen SIMBG Otomatis")
    
    with st.expander(f"Buka Panel Laporan & RKS (Step-by-Step)", expanded=True):
        st.info(f"Menggunakan Persona: **{persona_name}**")
        
        jenis_dokumen = st.radio(
            "Pilih Jenis Dokumen yang Akan Dicetak:",
            ["Laporan Perhitungan Teknis (DED)", "Spesifikasi Teknis / Syarat-Syarat (RKS)"],
            horizontal=True
        )
        
        target_prompt_category = "RKS" if "RKS" in jenis_dokumen else module_category

        c1, c2 = st.columns([3, 1])
        with c1:
            project_name = st.text_input("Nama Proyek:", "PROYEK STRATEGIS NASIONAL", key=f"proj_{module_category}")
            extra_ctx = st.text_area("Data Tambahan (Mutu Material / Lokasi):", placeholder="Misal: Beton K-350, Baja tulangan fy 420 MPa...", key=f"ctx_{module_category}")
        
        # ==========================================================
        # INISIALISASI SESSION STATE (UNTUK FITUR NEXT-NEXT)
        # ==========================================================
        state_key_step = f"step_{module_category}"
        state_key_report = f"report_{module_category}"
        state_key_chat = f"chat_{module_category}"
        
        # Set nilai awal jika belum ada
        if state_key_step not in st.session_state:
            st.session_state[state_key_step] = 0
            st.session_state[state_key_report] = ""
            st.session_state[state_key_chat] = None

        prompts = prompt_registry.get_chain_prompts(target_prompt_category, project_name, extra_ctx)
        total_steps = len(prompts)
        current_step = st.session_state[state_key_step]

        # Tombol Reset (Bila ingin mengulang dari awal)
        with c2:
            st.write("")
            if st.button("🔄 Reset / Ulang", use_container_width=True, key=f"reset_{module_category}"):
                st.session_state[state_key_step] = 0
                st.session_state[state_key_report] = ""
                st.session_state[state_key_chat] = None
                st.rerun()

        st.divider()

        # ==========================================================
        # TAMPILAN PROGRESS & PREVIEW DOKUMEN
        # ==========================================================
        if current_step > 0:
            st.progress(current_step / total_steps)
            st.caption(f"**Progress:** Bab {current_step} dari {total_steps} selesai.")
            
            # Preview Laporan yang Sedang Diketik
            st.markdown("**Preview Dokumen Sementara:**")
            with st.container(height=300):
                st.markdown(st.session_state[state_key_report])

        # ==========================================================
        # LOGIC TOMBOL "NEXT / GENERATE"
        # ==========================================================
        if current_step < total_steps:
            btn_label = "⚡ MULAI GENERATE (BAB 1)" if current_step == 0 else f"⚡ LANJUT GENERATE (BAB {current_step + 1})"
            
            if st.button(btn_label, type="primary", use_container_width=True, key=f"btn_next_{module_category}"):
                with st.spinner(f"AI sedang mengetik Bab {current_step + 1}... (Mohon tunggu)"):
                    try:
                        # 1. Inisiasi AI & Format Judul (Hanya saat Langkah Pertama)
                        if st.session_state[state_key_chat] is None:
                            SYS_PROMPT = f"Anda adalah {persona_name}. Buat dokumen formal. JANGAN MERINGKAS."
                            # Gunakan fitur Auto-Fallback untuk mencegah Error 404
                            model, used_model_name = get_working_model(SYS_PROMPT)
                            
                            st.session_state[state_key_chat] = model.start_chat(history=[])
                            
                            judul_pdf = "RENCANA KERJA DAN SYARAT-SYARAT (RKS)" if target_prompt_category == "RKS" else f"LAPORAN TEKNIS {module_category}"
                            st.session_state[state_key_report] = f"# {judul_pdf}\n**PROYEK: {project_name}**\n\n"

                        # 2. Kirim Prompt Sesuai Urutan
                        chat = st.session_state[state_key_chat]
                        prompt_text = prompts[current_step]
                        
                        response = chat.send_message(prompt_text)
                        
                        # 3. Simpan Hasil dan Maju ke Step Berikutnya
                        st.session_state[state_key_report] += response.text + "\n\n"
                        st.session_state[state_key_step] += 1
                        
                        # Rerun untuk me-refresh tampilan UI
                        st.rerun()

                    except Exception as e:
                        st.error(f"Terjadi Kesalahan Jaringan/AI: {e}\n\nSilakan klik tombol 'Lanjut' lagi untuk mencoba ulang (Resume).")
        
        # ==========================================================
        # JIKA SEMUA BAB SELESAI -> MUNCULKAN TOMBOL DOWNLOAD PDF
        # ==========================================================
        else:
            st.success("✅ **Seluruh dokumen telah selesai dikompilasi!**")
            judul_pdf = "RENCANA KERJA DAN SYARAT-SYARAT (RKS)" if target_prompt_category == "RKS" else f"LAPORAN TEKNIS {module_category}"
            
            try:
                pdf_data = libs_pdf.create_pdf(st.session_state[state_key_report], title=judul_pdf)
                st.download_button(
                    label=f"📥 DOWNLOAD PDF ({judul_pdf})",
                    data=pdf_data,
                    file_name=f"Dokumen_{target_prompt_category}_{project_name.replace(' ','_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key=f"dl_final_{module_category}"
                )
            except Exception as e:
                st.error(f"Gagal mengonversi ke PDF: {e}")
