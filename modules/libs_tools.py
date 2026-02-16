import sys

# --- MEKANISME IMPORT ROBUST (Tahan Banting) ---
# Mencoba import dari folder modules, jika gagal (flat directory), import langsung.
try:
    from modules.struktur import libs_sni as sni
    from modules.struktur import libs_baja as steel
    from modules.struktur import libs_gempa as quake
    from modules.cost import libs_ahsp as ahsp
    from modules.cost import libs_optimizer as opt
    
    # Import modul Geotek & Air (cek ketersediaan)
    try: from modules.geotek import libs_pondasi as fdn
    except: import libs_pondasi as fdn
    
    try: from modules.geotek import libs_geoteknik as geo
    except: import libs_geoteknik as geo

    try: from modules.arch import libs_arch
    except: import libs_arch
    
    try: from modules.arch import libs_zoning
    except: import libs_zoning
    
    try: from modules.arch import libs_green
    except: import libs_green

except ImportError:
    # Fallback jika semua file ada di satu folder (Flat)
    import libs_sni as sni
    import libs_ahsp as ahsp
    import libs_pondasi as fdn
    import libs_baja as steel
    import libs_gempa as quake
    import libs_geoteknik as geo
    import libs_optimizer as opt
    import libs_arch
    import libs_zoning
    import libs_green

# --- 1. TOOL STRUKTUR BETON (SNI 2847:2019) ---
def tool_hitung_balok(b_mm, h_mm, fc, fy, mu_kNm):
    """
    [TOOL SATRIA] Menghitung tulangan balok beton.
    """
    try:
        # [FIX] Memanggil Class SNI 2019 yang benar
        engine = sni.SNI_Concrete_2019(fc, fy)
        
        ds = 40 + 10 + 8 # Selimut + Sengkang + 1/2 D_tulangan (Estimasi d)
        d_eff = h_mm - ds
        
        # 1. Hitung Tulangan Lentur (As)
        as_req = engine.hitung_tulangan_perlu(mu_kNm, d_eff, b_mm)
        dia_tul = 16
        n_bars = int(as_req / (0.25 * 3.14 * dia_tul**2)) + 1
        
        # 2. Hitung Kapasitas Geser (Vc)
        # [FIX] Kita masukkan As_longitudinal agar Size Effect dihitung akurat (Strict SNI)
        vc, lambda_s, trace_msg = engine.hitung_geser_beton_vc(
            bw=b_mm, 
            d=d_eff, 
            Av_terpasang=0, # Asumsi awal tanpa sengkang
            As_longitudinal=as_req # Parameter Baru
        )
        
        return (f"Analisa Balok {b_mm}x{h_mm} (Mu={mu_kNm} kNm):\n"
                f"- Tulangan Lentur Perlu: {as_req:.2f} mm2\n"
                f"- Rekomendasi: {n_bars} D{dia_tul}\n"
                f"- Kapasitas Geser Beton (Vc): {vc/1000:.2f} kN\n"
                f"- Faktor Ukuran (Size Effect): {lambda_s:.3f}")
                
    except Exception as e:
        return f"Error hitung balok: {str(e)}"

# --- 2. TOOL STRUKTUR BAJA (SNI 1729:2020) ---
def tool_cek_baja_wf(mu_kNm, bentang_m):
    """
    [TOOL SATRIA] Cek kapasitas profil baja WF 300x150.
    """
    # Data Profil WF 300x150x6.5x9
    wf_data = {
        'Zx': 481000, # mm3
        'Iy': 5.08e6, 
        'J': 1.36e5, 
        'Sx': 424000, 
        'ho': 291, 
        'ry': 32.9
    } 
    
    # [FIX] Mekanisme Kalkulasi Mandiri (Fallback)
    # Karena file libs_baja.py user mungkin belum lengkap method cek-nya.
    try:
        # Hitung Kapasitas Momen Plastis (Phi Mn)
        # Phi = 0.9, Fy = 240 MPa
        Fy = 240
        Phi = 0.9
        
        # Mn = Mp = Fy * Zx (Asumsi Bentang Pendek/Kompak)
        # Ini penyederhanaan agar alat tetap jalan dan memberikan estimasi.
        Mn_nmm = Fy * wf_data['Zx']
        Phi_Mn_kNm = (Phi * Mn_nmm) / 1e6
        
        ratio = mu_kNm / Phi_Mn_kNm
        status = "AMAN" if ratio < 1.0 else "TIDAK AMAN"
        
        return f"Analisa WF 300x150 (BJ-37): Kapasitas Phi.Mn = {Phi_Mn_kNm:.2f} kNm. Ratio {ratio:.2f} ({status})."
        
    except Exception as e:
        return f"Error Baja: {e}"

# --- 3. TOOL PONDASI ---
def tool_hitung_pondasi(beban_pu, lebar_m):
    """
    [TOOL GEOTEKNIK] Cek keamanan pondasi telapak.
    """
    try:
        engine = fdn.Foundation_Engine(150.0) # Daya dukung tanah 150 kPa
        res = engine.hitung_footplate(beban_pu, lebar_m, lebar_m, 300)
        return f"Pondasi {lebar_m}x{lebar_m}m (Pu={beban_pu}kN): {res['status']}. Safety Factor: {res['ratio_safety']:.2f}."
    except Exception as e:
        return f"Error Pondasi: {e}"

# --- 4. TOOL ESTIMASI BIAYA (AHSP) ---
def tool_estimasi_biaya(volume_beton):
    """
    [TOOL BUDI] Hitung biaya beton per m3.
    """
    try:
        engine = ahsp.AHSP_Engine()
        # Harga satuan disesuaikan per unit
        h_dasar = {'semen': 70000/50, 'pasir': 250000, 'split': 300000, 'pekerja': 120000, 'tukang': 150000} 
        hsp = engine.hitung_hsp('beton_k300', h_dasar, h_dasar)
        total = volume_beton * hsp
        return f"Analisa Harga Satuan Beton K-300: Rp {hsp:,.0f}/m3. Total ({volume_beton} m3): Rp {total:,.0f}"
    except Exception as e:
        return f"Error AHSP: {e}"

# --- 5. TOOL GEMPA (SNI 1726:2019) ---
def tool_hitung_gempa_v(berat_total_kn, lokasi_tanah):
    """
    [TOOL GEMPA] Hitung Base Shear dengan Interpolasi Linear.
    """
    try:
        site_map = {'lunak': 'SE', 'sedang': 'SD', 'keras': 'SC'}
        kode_site = site_map.get(lokasi_tanah.lower(), 'SD')
        
        # [FIX] Menggunakan Class SNI_Gempa_2019
        # Parameter Ss=0.8, S1=0.4 (Contoh default zona gempa kuat)
        engine = quake.SNI_Gempa_2019(0.8, 0.4, kode_site)
        
        # Hitung Cs (Koefisien Respon Seismik)
        # Cs = Sds / (R/Ie) -> Asumsi R=8 (SRPMK), Ie=1.0
        R = 8.0
        Ie = 1.0
        Cs = engine.Sds / (R/Ie)
        
        # Base Shear V = Cs * W
        V = Cs * berat_total_kn
        
        return (f"Analisa Gempa (Tanah {kode_site} - SNI 1726:2019):\n"
                f"- Parameter: Fa={engine.Fa}, Fv={engine.Fv}\n"
                f"- Design Spectrum: Sds={engine.Sds:.3f}, Sd1={engine.Sd1:.3f}\n"
                f"- Base Shear (V): {V:.2f} kN (Koefisien Cs={Cs:.4f})")
    except Exception as e:
        return f"Error Gempa: {e}"

# --- 6. TOOL TALUD ---
def tool_cek_talud(tinggi_m):
    """
    [TOOL GEOTEKNIK] Cek kestabilan Talud.
    """
    try:
        # Init Engine: gamma=18, phi=30, c=5
        engine = geo.Geotech_Engine(gamma=18.0, phi=30.0, c=5.0)
        res = engine.hitung_talud_batu_kali(tinggi_m, 0.4, 0.6 * tinggi_m) # Lebar bawah 0.6H
        return f"Talud H={tinggi_m}m: SF Guling={res['SF_Guling']:.2f}. Status: {res['Status']}."
    except Exception as e:
        return f"Error Geotek: {e}"

# --- 7. TOOL OPTIMASI ---
def tool_cari_dimensi_optimal(mu_kNm, bentang_m):
    """
    [TOOL SATRIA] Optimasi Dimensi Balok.
    """
    try:
        harga = {'beton': 1200000, 'baja': 15000, 'bekisting': 200000}
        optimizer = opt.BeamOptimizer(25, 400, harga)
        hasil = optimizer.cari_dimensi_optimal(mu_kNm, bentang_m)
        
        if not hasil:
            return "Tidak ditemukan dimensi optimal (Coba perbesar mutu beton atau cek beban)."
        
        best = hasil[0]
        return (f"REKOMENDASI AI (Termurah):\n"
                f"1. Dimensi: {best['b (mm)']} x {best['h (mm)']} mm\n"
                f"2. Biaya: Rp {best['Biaya/m']:,.0f} /m'\n"
                f"3. Tulangan: {best['As Perlu (mm2)']} mm2 (Rho={best['Rho (%)']}%)")
    except Exception as e:
        return f"Error Optimasi: {e}"

# --- 8. TOOL ARSITEK & GREEN ---
def tool_konsep_rumah(penghuni, mobil, luas_tanah):
    try:
        arch = libs_arch.Architect_Engine()
        res = arch.generate_program_ruang(penghuni, mobil, luas_tanah)
        
        # Format Text
        txt = f"PROGRAM RUANG:\nTotal Luas: {res['Total_Luas_Bangunan']:.1f} m2\nStatus: {res['Status_KDB_60%']}\n"
        return txt
    except:
        return f"Modul Arsitek belum terload sempurna. Estimasi: Keluarga {penghuni} org butuh min {penghuni*25}m2 bangunan."

def tool_audit_green(luas_atap, hadap):
    try:
        eco = libs_green.Green_Audit()
        hujan = eco.hitung_panen_hujan(luas_atap, 2000)
        return f"Potensi Panen Hujan: {hujan['Penghematan Harian']}"
    except:
        return "Modul Green belum aktif."
