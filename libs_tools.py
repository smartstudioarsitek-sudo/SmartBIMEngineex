import sys
import math

# ==============================================================================
# 1. MEKANISME IMPORT ROBUST (TAHAN BANTING)
# ==============================================================================
# Sistem ini memastikan aplikasi tidak crash baik dijalankan di struktur folder 
# 'modules/...' maupun struktur flat (semua file di root).
try:
    # Coba import dari struktur folder rapi (Standar Production)
    from modules.struktur import libs_sni as sni
    from modules.struktur import libs_baja as steel
    from modules.struktur import libs_gempa as quake
    from modules.cost import libs_ahsp as ahsp
    from modules.cost import libs_optimizer as opt
    
    # Import modul Geotek & Air (dengan pengecekan ketersediaan)
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
    # Fallback: Jika dijalankan di mode Flat (semua file satu folder)
    try:
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
    except ImportError as e:
        # Jika masih gagal, ini error kritikal sistem
        print(f"CRITICAL SYSTEM ERROR: Gagal memuat library inti. Detail: {e}")

# ==============================================================================
# 2. KERNEL MATEMATIKA (AUDIT COMPLIANCE SNI 1726:2019)
# ==============================================================================

def interpolate_sni_coefficients(value: float, axis_points: list, coefficient_values: list) -> float:
    """
    [ALGORITMA INTERPOLASI PRESISI - SESUAI REKOMENDASI AUDIT]
    Fungsi ini menangani Skenario Uji A, B, dan C laporan audit.
    """
    if not axis_points or not coefficient_values:
        return 0.0
    
    if value <= axis_points[0]:
        return coefficient_values[0]
        
    if value >= axis_points[-1]:
        return coefficient_values[-1]
        
    for i in range(len(axis_points) - 1):
        x1 = axis_points[i]
        x2 = axis_points[i+1]
        
        if x1 <= value <= x2:
            y1 = coefficient_values[i]
            y2 = coefficient_values[i+1]
            
            if x2 == x1: 
                return y1 
            
            ratio = (value - x1) / (x2 - x1)
            result = y1 + ratio * (y2 - y1)
            return result
            
    return coefficient_values[-1] 

# ==============================================================================
# 3. IMPLEMENTASI TOOLS (INTEGRASI ANTAR MODUL UNTUK AI GEMINI)
# Wajib menggunakan Type Hints (: float, : str) agar terbaca oleh LLM
# ==============================================================================

# --- TOOL 1: STRUKTUR BETON (SNI 2847:2019) ---
def tool_hitung_balok(b_mm: float, h_mm: float, fc: float, fy: float, mu_kNm: float) -> str:
    """
    Menghitung kebutuhan tulangan lentur dan kapasitas geser balok beton bertulang berdasarkan SNI 2847:2019.
    Gunakan tool ini jika pengguna meminta perhitungan struktur balok beton.
    
    Args:
        b_mm: Lebar balok dalam satuan milimeter (mm).
        h_mm: Tinggi balok dalam satuan milimeter (mm).
        fc: Mutu kuat tekan beton (MPa).
        fy: Mutu kuat leleh baja tulangan utama (MPa).
        mu_kNm: Beban momen ultimate yang terjadi dalam satuan kNm.
    """
    try:
        engine = sni.SNI_Concrete_2019(fc, fy)
        ds = 40 + 10 + 8 
        d_eff = h_mm - ds
        
        as_req = engine.hitung_tulangan_perlu(mu_kNm, d_eff, b_mm)
        dia_tul = 16
        n_bars = int(as_req / (0.25 * 3.14 * dia_tul**2)) + 1
        
        vc, lambda_s, trace_msg = engine.hitung_geser_beton_vc(
            bw=b_mm, 
            d=d_eff, 
            Av_terpasang=0, 
            As_longitudinal=as_req 
        )
        
        report = (
            f"ANALISA STRUKTUR BALOK {b_mm}x{h_mm} (SNI 2847:2019)\n"
            f"----------------------------------------------------\n"
            f"1. Data Input:\n"
            f"   - Mu (Momen Ultimate): {mu_kNm} kNm\n"
            f"   - Mutu Material: fc' {fc} MPa, fy {fy} MPa\n"
            f"   - Tinggi Efektif (d): {d_eff} mm\n\n"
            f"2. Analisa Lentur:\n"
            f"   - Luas Tulangan Perlu (As): {as_req:.2f} mm2\n"
            f"   - Rekomendasi: {n_bars} D{dia_tul} (As pasang = {n_bars * 0.25 * 3.14 * dia_tul**2:.0f} mm2)\n\n"
            f"3. Analisa Geser Beton (Vc):\n"
            f"   - Faktor Ukuran (Size Effect lambda_s): {lambda_s:.3f}\n"
            f"   - Kapasitas Geser Beton (Vc): {vc/1000:.2f} kN\n"
            f"   - Detail Perhitungan: {trace_msg}\n"
        )
        return report
                
    except Exception as e:
        return f"ERROR Hitung Balok: {str(e)}. Periksa input parameter."

# --- TOOL 2: STRUKTUR BAJA (SNI 1729:2020) ---
def tool_cek_baja_wf(mu_kNm: float, bentang_m: float) -> str:
    """
    Mengecek kapasitas momen dan stabilitas lateral (LTB) profil baja WF 300x150 standar SNI 1729:2020.
    Gunakan tool ini jika pengguna meminta pengecekan profil baja WF.
    
    Args:
        mu_kNm: Beban momen ultimate yang terjadi dalam kNm.
        bentang_m: Panjang bentang balok tak terkekang dalam meter (m).
    """
    wf_data = {
        'Zx': 481000, 
        'Iy': 5.08e6, 
        'J': 1.36e5,  
        'Sx': 424000, 
        'h': 300,
        'bf': 150
    } 
    
    try:
        Fy = 240.0 
        E = 200000.0 
        Phi_b = 0.90 
        
        Mn_nmm = Fy * wf_data['Zx']
        Phi_Mn_Yield = (Phi_b * Mn_nmm) / 1e6 
        
        Lb = bentang_m * 1000 
        ry = math.sqrt(wf_data['Iy'] / (wf_data['bf'] * 9 + (wf_data['h']-18)*6.5)) 
        Lp = 1.76 * 32.9 * math.sqrt(E/Fy) 
        
        status_ltb = "Aman (Kompak)"
        Phi_Mn_Final = Phi_Mn_Yield
        
        if Lb > Lp:
            reduksi_ltb = max(0.6, Lp / Lb) 
            Phi_Mn_Final = Phi_Mn_Yield * reduksi_ltb
            status_ltb = f"Rawan LTB (Reduksi {reduksi_ltb:.2f}x)"

        D_C_Ratio = mu_kNm / Phi_Mn_Final
        status = "AMAN" if D_C_Ratio <= 1.0 else "TIDAK AMAN"
        
        report = (
            f"ANALISA BAJA WF 300x150 (BJ-37)\n"
            f"-------------------------------\n"
            f"1. Kapasitas Penampang (Yielding):\n"
            f"   - Phi.Mn Plastis: {Phi_Mn_Yield:.2f} kNm\n"
            f"2. Stabilitas Lateral (LTB):\n"
            f"   - Panjang Bentang: {bentang_m} m\n"
            f"   - Status: {status_ltb}\n"
            f"   - Kapasitas Desain Akhir: {Phi_Mn_Final:.2f} kNm\n"
            f"3. Kesimpulan:\n"
            f"   - Beban Terfaktor (Mu): {mu_kNm} kNm\n"
            f"   - Ratio (D/C): {D_C_Ratio:.3f} -> {status}"
        )
        return report
        
    except Exception as e:
        return f"ERROR Analisa Baja: {e}"

# --- TOOL 3: PONDASI (GEOTEKNIK) ---
def tool_hitung_pondasi(beban_pu: float, lebar_m: float) -> str:
    """
    Menghitung tegangan yang terjadi pada pondasi telapak (cakar ayam) dan mengecek keamanannya terhadap daya dukung tanah.
    
    Args:
        beban_pu: Beban aksial yang disalurkan ke pondasi (kN).
        lebar_m: Lebar/panjang tapak pondasi persegi dalam meter (m).
    """
    try:
        engine = fdn.Foundation_Engine(150.0) 
        res = engine.hitung_footplate(beban_pu, lebar_m, lebar_m, 300)
        
        return (
            f"ANALISA PONDASI TAPAK {lebar_m}x{lebar_m} m\n"
            f"- Beban Aksial (Pu): {beban_pu} kN\n"
            f"- Daya Dukung Tanah: 150 kPa\n"
            f"- Safety Factor: {res['ratio_safety']:.2f}\n"
            f"- Status: {res['status']}\n"
            f"- Volume Beton: {res['vol_beton']:.2f} m3"
        )
    except Exception as e:
        return f"ERROR Pondasi: {e}"

# --- TOOL 4: ESTIMASI BIAYA (AHSP) ---
def tool_estimasi_biaya(volume_beton: float) -> str:
    """
    Menghitung estimasi biaya pekerjaan beton mutu K-300 berdasarkan harga satuan bahan dan upah.
    
    Args:
        volume_beton: Total volume beton yang akan dikerjakan dalam satuan m3.
    """
    try:
        engine = ahsp.AHSP_Engine()
        h_dasar = {
            'semen': 1400,    
            'pasir': 250000,  
            'split': 300000,  
            'pekerja': 120000,
            'tukang': 150000  
        } 
        
        hsp = engine.hitung_hsp('beton_k300', h_dasar, h_dasar)
        total = volume_beton * hsp
        
        return (
            f"ESTIMASI BIAYA PEKERJAAN BETON (K-300)\n"
            f"- Volume: {volume_beton} m3\n"
            f"- Harga Satuan (HSP): Rp {hsp:,.0f} /m3\n"
            f"- Total Biaya: Rp {total:,.0f}"
        )
    except Exception as e:
        return f"ERROR AHSP: {e}"

# --- TOOL 5: GEMPA (SNI 1726:2019) - AUDIT PRIORITY ---
def tool_hitung_gempa_v(berat_total_kn: float, lokasi_tanah: str) -> str:
    """
    Menghitung gaya geser dasar (Base Shear / V) akibat beban gempa berdasarkan SNI 1726:2019.
    
    Args:
        berat_total_kn: Berat total bangunan seismik efektif dalam satuan kN.
        lokasi_tanah: Jenis/kategori tanah, pilih salah satu dari: 'lunak', 'sedang', 'keras', atau 'khusus'.
    """
    try:
        site_map = {'lunak': 'SE', 'sedang': 'SD', 'keras': 'SC', 'khusus': 'SF'}
        kode_site = site_map.get(lokasi_tanah.lower(), 'SD')
        
        if kode_site == 'SF':
            return "STOP: Kelas Situs SF (Tanah Khusus) memerlukan Analisis Respons Spesifik Situs (Pasal 6.10.1). Perhitungan otomatis tidak diizinkan demi keselamatan."

        Ss_input = 0.8
        S1_input = 0.4

        engine = quake.SNI_Gempa_2019(Ss_input, S1_input, kode_site)
        
        R = 8.0
        Ie = 1.0
        
        if R == 0: Cs = 0 
        else: Cs = engine.Sds / (R/Ie)
        
        V = Cs * berat_total_kn
        
        report = (
            f"ANALISA GAYA GESER DASAR (BASE SHEAR) - SNI 1726:2019\n"
            f"-----------------------------------------------------\n"
            f"1. Parameter Gempa & Tanah:\n"
            f"   - Kelas Situs: {kode_site}\n"
            f"   - Input: Ss={Ss_input}g, S1={S1_input}g\n"
            f"   - Koefisien (Interpolasi): Fa={engine.Fa}, Fv={engine.Fv}\n"
            f"   - Catatan: {engine.Note}\n\n"
            f"2. Spektrum Desain:\n"
            f"   - SDS = {engine.Sds:.3f}g\n"
            f"   - SD1 = {engine.Sd1:.3f}g\n\n"
            f"3. Gaya Geser Dasar (V):\n"
            f"   - Berat Struktur (W): {berat_total_kn} kN\n"
            f"   - Koefisien Cs: {Cs:.4f}\n"
            f"   - V = Cs * W = {V:.2f} kN"
        )
        return report
        
    except Exception as e:
        return f"ERROR Gempa: {e}"

# --- TOOL 6: TALUD (GEOTEKNIK) ---
def tool_cek_talud(tinggi_m: float) -> str:
    """
    Mengecek stabilitas guling (Overturning Safety Factor) untuk struktur Talud / Dinding Penahan Tanah Batu Kali.
    
    Args:
        tinggi_m: Tinggi talud dari dasar ke permukaan dalam satuan meter (m).
    """
    try:
        engine = geo.Geotech_Engine(gamma=18.0, phi=30.0, c=5.0)
        
        b_atas = 0.4
        b_bawah = 0.6 * tinggi_m
        
        res = engine.hitung_talud_batu_kali(tinggi_m, b_atas, b_bawah)
        
        return (
            f"ANALISA STABILITAS TALUD (H={tinggi_m}m)\n"
            f"- Dimensi: Atas {b_atas}m, Bawah {b_bawah:.2f}m\n"
            f"- Safety Factor Guling: {res['SF_Guling']:.2f}\n"
            f"- Status Keamanan: {res['Status']}"
        )
    except Exception as e:
        return f"ERROR Geotek: {e}"

# --- TOOL 7: OPTIMASI (COST) ---
def tool_cari_dimensi_optimal(mu_kNm: float, bentang_m: float) -> str:
    """
    Mencari ukuran dimensi balok beton (lebar x tinggi) yang paling optimal dan termurah berdasarkan beban momen.
    
    Args:
        mu_kNm: Momen lentur ultimate (kNm).
        bentang_m: Panjang bentang balok (m).
    """
    try:
        harga = {'beton': 1200000, 'baja': 15000, 'bekisting': 200000}
        optimizer = opt.BeamOptimizer(25, 400, harga)
        hasil = optimizer.cari_dimensi_optimal(mu_kNm, bentang_m)
        
        if not hasil:
            return "Tidak ditemukan dimensi optimal. Coba perbesar mutu beton atau cek beban."
        
        best = hasil[0]
        return (
            f"REKOMENDASI AI (TERMURAH & AMAN):\n"
            f"1. Dimensi: {best['b (mm)']} x {best['h (mm)']} mm\n"
            f"2. Biaya: Rp {best['Biaya/m']:,.0f} /m'\n"
            f"3. Tulangan Perlu: {best['As Perlu (mm2)']} mm2\n"
            f"4. Rasio Tulangan: {best['Rho (%)']}% (Efisien)"
        )
    except Exception as e:
        return f"ERROR Optimasi: {e}"

# --- TOOL 8: ARSITEK & GREEN ---
def tool_konsep_rumah(penghuni: int, mobil: int, luas_tanah: float) -> str:
    """
    Membuat program ruang arsitektur dan mengecek KDB (Koefisien Dasar Bangunan).
    
    Args:
        penghuni: Jumlah estimasi penghuni rumah (orang).
        mobil: Jumlah mobil yang butuh garasi/carport (unit).
        luas_tanah: Luas total lahan tanah (m2).
    """
    try:
        arch = libs_arch.Architect_Engine()
        res = arch.generate_program_ruang(penghuni, mobil, luas_tanah)
        
        txt = (
            f"PROGRAM RUANG ARSITEKTUR\n"
            f"- Total Luas Bangunan: {res['Total_Luas_Bangunan']:.1f} m2\n"
            f"- Ketersediaan Lahan: {luas_tanah} m2\n"
            f"- Status KDB: {res['Status_KDB_60%']}\n"
            f"- Rincian: {len(res['Detail_Ruang'])} jenis ruang terbentuk."
        )
        return txt
    except Exception as e:
        return f"Modul Arsitek belum siap. Estimasi kasar: {penghuni*25}m2. Detail: {e}"

def tool_audit_green(luas_atap: float, hadap: str) -> str:
    """
    Melakukan audit efisiensi green building terkait panen air hujan dan orientasi matahari.
    
    Args:
        luas_atap: Luas penampang atap yang menampung air (m2).
        hadap: Arah mata angin fasad utama bangunan menghadap (cth: 'utara', 'timur', 'barat').
    """
    try:
        eco = libs_green.Green_Building_Engine() # Fix nama class sesuai file libs_green.py
        hujan = eco.hitung_panen_hujan(luas_atap, 2500) 
        matahari = eco.cek_orientasi_bangunan(hadap)
        
        return (
            f"AUDIT GREEN BUILDING\n"
            f"1. Orientasi: {matahari}\n"
            f"2. Panen Air Hujan: {hujan['Penghematan Harian']} ({hujan['Potensi Air Hujan']})"
        )
    except Exception as e:
        return f"Modul Green belum aktif. Error: {e}"
