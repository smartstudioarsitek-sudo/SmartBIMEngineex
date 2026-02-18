import streamlit as st
import google.generativeai as genai
from modules.utils import libs_pdf
from modules.utils import prompt_registry # <--- PENTING: Import registry yg baru dibuat

def render_auto_chain_panel(module_category, persona_name):
    """
    Panel Generator Laporan Universal
    module_category: "STRUKTUR", "WATER", "COST", "ARSITEK", "GEOTEK"
    """
    
    st.markdown("---")
    st.subheader(f"🚀 Generator Laporan Otomatis: {module_category}")
    
    # Warna border berbeda tiap modul (Kosmetik)
    border_color = "#1E3A8A" if module_category == "STRUKTUR" else "#059669"
    
    with st.expander(f"Buka Panel Laporan {module_category}", expanded=False):
        st.info(f"Menggunakan Persona: **{persona_name}**")
        
        c1, c2 = st.columns([3, 1])
        with c1:
            project_name = st.text_input("Nama Proyek:", "PROYEK STRATEGIS NASIONAL", key=f"proj_{module_category}")
            extra_ctx = st.text_area("Data Tambahan (Opsional):", placeholder="Misal: Tanah lunak, Lokasi IKN, Beton K-300...", key=f"ctx_{module_category}")
        with c2:
            st.write("") 
            # Key unik agar tidak bentrok antar menu
            btn_start = st.button(f"⚡ RUN {module_category}", type="primary", use_container_width=True, key=f"btn_{module_category}")

        if btn_start:
            # 1. Ambil Prompt dari Registry
            prompts = prompt_registry.get_chain_prompts(module_category, project_name, extra_ctx)
            
            if not prompts:
                st.error("Template laporan belum tersedia.")
                return

            # 2. Setup AI
            SYS_PROMPT = f"Anda adalah {persona_name}. Buat Laporan Teknis Detail. JANGAN MERINGKAS."
            try:
                model = genai.GenerativeModel("gemini-flash-latest", system_instruction=SYS_PROMPT)
                chat = model.start_chat(history=[])
            except Exception as e:
                st.error(f"Gagal koneksi AI: {e}")
                return
            
            full_report = f"# LAPORAN TEKNIS: {project_name}\n**MODUL: {module_category}**\n\n"
            status_box = st.status("Memulai inisialisasi...", expanded=True)
            placeholder = st.empty()
            prog_bar = st.progress(0)

            try:
                total_parts = len(prompts)
                for i, prompt_text in enumerate(prompts):
                    part_num = i + 1
                    status_box.write(f"⏳ Mengerjakan Bagian {part_num} dari {total_parts}...")
                    
                    response = chat.send_message(prompt_text)
                    full_report += response.text + "\n\n---\n\n"
                    placeholder.markdown(full_report + f"\n\n*Menyiapkan bagian selanjutnya...*")
                    prog_bar.progress(int((part_num / total_parts) * 100))
                
                status_box.update(label="✅ Selesai!", state="complete", expanded=False)
                placeholder.markdown(full_report)
                
                # PDF
                pdf_data = libs_pdf.create_pdf(full_report, title=f"LAPORAN {module_category}")
                st.download_button(
                    label="📥 Download PDF Lengkap",
                    data=pdf_data,
                    file_name=f"Laporan_{module_category}_{project_name.replace(' ','_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    key=f"dl_{module_category}"
                )

            except Exception as e:
                status_box.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")
