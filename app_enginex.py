# --- B. MODE FEM (ANALISIS GEMPA) ---
elif selected_menu == "🌪️ Analisis Gempa (FEM)":
    st.header("🌪️ Analisis Gempa Dinamis (FEM Engine)")
    
    # Import Module Peta Gempa
    from modules.struktur.peta_gempa_indo import get_data_kota, hitung_respon_spektrum

    # --- 1. DATA LOKASI & TANAH (FITUR BARU) ---
    with st.expander("🌍 Lokasi & Data Gempa (SNI 1726:2019)", expanded=True):
        c_loc1, c_loc2 = st.columns(2)
        
        with c_loc1:
            db_kota = get_data_kota()
            pilihan_kota = st.selectbox("📍 Pilih Lokasi Proyek", list(db_kota.keys()), index=8) # Default Lampung
            
            # Ambil data Ss dan S1
            data_gempa = db_kota[pilihan_kota]
            
            # Kalau user pilih manual, boleh edit. Kalau kota, disable edit biar aman.
            is_manual = (pilihan_kota == "Pilih Manual")
            
            Ss_input = st.number_input("Parameter Ss (0.2 detik)", value=data_gempa['Ss'], disabled=not is_manual, format="%.2f")
            S1_input = st.number_input("Parameter S1 (1.0 detik)", value=data_gempa['S1'], disabled=not is_manual, format="%.2f")

        with c_loc2:
            kelas_situs = st.selectbox("🪨 Kelas Situs Tanah", ["SA (Batuan Keras)", "SB (Batuan)", "SC (Tanah Keras)", "SD (Tanah Sedang)", "SE (Tanah Lunak)"])
            kode_situs = kelas_situs.split()[0] # Ambil SA, SB, dst
            
            # Hitung Otomatis Parameter Desain
            hasil_gempa = hitung_respon_spektrum(Ss_input, S1_input, kode_situs)
            
            st.info(f"📊 **Parameter Desain (Otomatis):**\n\n"
                    f"**SDS = {hasil_gempa['SDS']:.3f} g** (Percepatan Desain Pendek)\n\n"
                    f"**SD1 = {hasil_gempa['SD1']:.3f} g** (Percepatan Desain 1-detik)")

    # --- 2. DATA STRUKTUR ---
    st.divider()
    st.subheader("🏗️ Geometri Struktur Portal")
    
    c1, c2 = st.columns(2)
    with c1:
        jml_lantai = st.number_input("Jumlah Lantai", 1, 50, 5)
        tinggi_lantai = st.number_input("Tinggi per Lantai (m)", 2.0, 6.0, 3.5)
    with c2:
        bentang_x = st.number_input("Bentang Arah X (m)", 3.0, 12.0, 6.0)
        bentang_y = st.number_input("Bentang Arah Y (m)", 3.0, 12.0, 6.0)
        fc_mutu = st.number_input("Mutu Beton (MPa)", 20, 60, 30)
    
    # --- 3. EKSEKUSI ---
    if st.button("🚀 Pre-Audit & Run Analysis", type="primary"):
        # Pre-Audit Sederhana
        if tinggi_lantai > 5.0 and fc_mutu < 25:
            st.error("⛔ **DITOLAK PRE-AUDIT:** Untuk tinggi tingkat > 5m, disarankan mutu beton minimal fc' 25 MPa.")
        elif 'libs_fem' not in sys.modules:
            st.error("❌ Modul FEM tidak ditemukan/gagal load.")
        else:
            with st.spinner(f"🔄 Menghitung Respon Spektrum {pilihan_kota}..."):
                try:
                    engine = libs_fem.OpenSeesEngine()
                    # Kita kirim data SDS juga ke engine (kalau engine-nya sudah support response spectrum)
                    # Untuk sekarang, engine modal analysis basic dulu
                    
                    engine.build_simple_portal(bentang_x, bentang_y, tinggi_lantai, jml_lantai, fc_mutu)
                    df_modal = engine.run_modal_analysis(num_modes=3)
                    
                    st.success("✅ Analisis Selesai & Lolos Validasi!")
                    
                    # Tampilkan Grafik Respon Spektrum (Visualisasi Baru)
                    st.subheader("📈 Kurva Respon Spektrum Desain")
                    
                    # Bikin plot kurva respons spektrum (T vs Sa)
                    T_vals = np.linspace(0, 4, 100)
                    Sa_vals = []
                    for t in T_vals:
                        if t < hasil_gempa['T0']: 
                            val = hasil_gempa['SDS'] * (0.4 + 0.6*t/hasil_gempa['T0'])
                        elif t < hasil_gempa['Ts']: 
                            val = hasil_gempa['SDS']
                        else: 
                            val = hasil_gempa['SD1'] / t
                        Sa_vals.append(val)
                        
                    fig_rsa = px.line(x=T_vals, y=Sa_vals, title=f"Respon Spektrum Desain ({pilihan_kota} - {kode_situs})")
                    fig_rsa.update_layout(xaxis_title="Periode T (detik)", yaxis_title="Percepatan Spektral Sa (g)")
                    st.plotly_chart(fig_rsa, use_container_width=True)

                    # Tampilkan Modal Analysis
                    st.subheader("📊 Mode Shapes & Perioda")
                    st.dataframe(df_modal, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"❌ Terjadi Kesalahan pada Engine FEM: {e}")
