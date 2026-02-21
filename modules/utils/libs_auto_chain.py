import streamlit as st
import google.generativeai as genai
from modules.utils import libs_pdf
from modules.utils import prompt_registry

def render_auto_chain_panel(module_category, persona_name):
    """
    Panel Generator Laporan Universal
    module_category: "STRUKTUR", "WATER", "COST", "ARSITEK", "GEOTEK"
    """
    st.markdown("---")
    st.subheader(f"🚀 Generator Dokumen SIMBG Otomatis")
    
    with st.expander(f"Buka Panel Laporan & RKS", expanded=False):
        st.info(f"Menggunakan Persona: **{persona_name}**")
        
        # --- FITUR BARU: PILIHAN JENIS DOKUMEN ---
        jenis_dokumen = st.radio(
            "Pilih Jenis Dokumen yang Akan Dicetak:",
            ["Laporan Perhitungan Teknis (DED)", "Spesifikasi Teknis / Syarat-Syarat (RKS)"],
            horizontal=True
        )
        
        # Tentukan Kategori Target berdasarkan pilihan Radio Button
        if "RKS" in jenis_dokumen:
            target_prompt_category = "RKS"
        else:
            target_prompt_category = module_category

        c1, c2 = st.columns([3, 1])
        with c1:
            project_name = st.text_input("Nama Proyek:", "PROYEK STRATEGIS NASIONAL", key=f"proj_{module_category}")
            extra_ctx = st.text_area("Data Tambahan (Mutu Material / Lokasi):", placeholder="Misal: Beton K-350, Baja tulangan fy 420 MPa...", key=f"ctx_{module_category}")
        with c2:
            st.write("") 
            btn_start = st.button(f"⚡ GENERATE DOKUMEN", type="primary", use_container_width=True, key=f"btn_{module_category}")

        if btn_start:
            # 1. Ambil Prompt dari Registry berdasarkan target yang dipilih
            prompts = prompt_registry.get_chain_prompts(target_prompt_category, project_name, extra_ctx)
            
            if not prompts:
                st.error("Template laporan belum tersedia.")
                return

            SYS_PROMPT = f"Anda adalah {persona_name}. Buat dokumen formal. JANGAN MERINGKAS."
            try:
                model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=SYS_PROMPT) # Gunakan flash agar cepat
                chat = model.start_chat(history=[])
            except Exception as e:
                st.error(f"Gagal koneksi AI: {e}")
                return
            
            # Header PDF
            judul_pdf = "RENCANA KERJA DAN SYARAT-SYARAT (RKS)" if target_prompt_category == "RKS" else f"LAPORAN TEKNIS {module_category}"
            full_report = f"# {judul_pdf}\n**PROYEK: {project_name}**\n\n"
            
            status_box = st.status("Memulai inisialisasi penulisan...", expanded=True)
            placeholder = st.empty()
            prog_bar = st.progress(0)

            try:
                total_parts = len(prompts)
                for i, prompt_text in enumerate(prompts):
                    part_num = i + 1
                    status_box.write(f"⏳ Mengerjakan Bab {part_num} dari {total_parts}...")
                    
                    response = chat.send_message(prompt_text)
                    full_report += response.text + "\n\n"
                    placeholder.markdown(full_report + f"\n\n*Mengetik bab selanjutnya...*")
                    prog_bar.progress(int((part_num / total_parts) * 100))
                
                status_box.update(label="✅ Selesai!", state="complete", expanded=False)
                placeholder.markdown(full_report)
                
                # Pembuatan PDF dengan libs_pdf yang sudah anti-alien
                pdf_data = libs_pdf.create_pdf(full_report, title=judul_pdf)
                st.download_button(
                    label=f"📥 Download PDF {target_prompt_category}",
                    data=pdf_data,
                    file_name=f"Dokumen_{target_prompt_category}_{project_name.replace(' ','_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    key=f"dl_{module_category}"
                )

            except Exception as e:
                status_box.update(label="❌ Error", state="error")
                st.error(f"Error AI: {e}")
