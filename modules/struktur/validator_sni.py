# File: modules/struktur/validator_sni.py

def cek_dimensi_kolom(b, h, lantai):
    """
    Validasi Dimensi Kolom berdasarkan SNI 2847:2019 (Pasal SRPMK).
    """
    pesan_error = []
    
    # 1. Cek Dimensi Minimum Absolut (200mm) - Tergantung SRPMK/SRPMM
    # Untuk keamanan gempa (SRPMM/SRPMK), minimum 300mm sering disarankan, tapi SNI membolehkan 200mm-250mm kondisi tertentu.
    if b < 200 or h < 200:
        pesan_error.append("⛔ **GAGAL (SNI 2847):** Dimensi kolom struktur tidak boleh kurang dari 200 mm.")

    # 2. Cek Rasio Dimensi (Tidak boleh terlalu pipih)
    # Rasio sisi terpendek : sisi tegak lurus tidak boleh kurang dari 0.4
    rasio = min(b, h) / max(b, h)
    if rasio < 0.4:
        pesan_error.append(f"⚠️ **PERINGATAN (Geometri):** Kolom terlalu pipih (Rasio {rasio:.2f} < 0.4). Berisiko saat gempa.")

    # 3. Cek Logika Tinggi Bangunan
    # Rule of Thumb: Lebar kolom ~ (Jumlah Lantai / 10) meter.
    # Misal 10 lantai -> butuh kolom +/- 1000mm (1 meter).
    min_b_rekomendasi = (lantai * 50) + 150 # Rumus empiris sederhana
    if b < min_b_rekomendasi or h < min_b_rekomendasi:
        pesan_error.append(f"⚠️ **PERINGATAN (Engineering Judgment):** Untuk {lantai} lantai, dimensi {b}x{h} mm terlihat terlalu kecil. Disarankan minimal {min_b_rekomendasi} mm.")

    return pesan_error

def cek_rasio_tulangan(b, h, n_tul, d_tul):
    """
    Validasi Rasio Tulangan (Rho) SNI 2847:2019.
    Batas aman: 1% s/d 8%. Ideal: 1% s/d 4%.
    """
    luas_penampang = b * h
    luas_tulangan = n_tul * 0.25 * 3.14159 * (d_tul ** 2)
    rho = (luas_tulangan / luas_penampang) * 100 # dalam Persen

    status = []
    
    if rho < 1.0:
        status.append(f"⛔ **GAGAL (SNI 2847):** Rasio tulangan ({rho:.2f}%) kurang dari minimum 1%. Struktur getas (mudah patah).")
    elif rho > 8.0:
        status.append(f"⛔ **GAGAL (SNI 2847):** Rasio tulangan ({rho:.2f}%) melebihi maksimum 8%. Beton sulit dicor (honeycomb).")
    elif rho > 4.0:
        status.append(f"⚠️ **PERINGATAN (Ekonomis):** Rasio tulangan ({rho:.2f}%) agak boros (> 4%). Pertimbangkan memperbesar dimensi beton.")
    
    return status, rho

def validasi_gempa_sni(kategori_gempa, sistem_struktur):
    """
    Validasi Sistem Struktur Penahan Gempa (SNI 1726:2019 Tabel 12).
    """
    saran = []
    
    if kategori_gempa in ['D', 'E', 'F']: # Wilayah Gempa Kuat (Palu, Padang, Jogja, dll)
        if sistem_struktur == "SRPMB" or sistem_struktur == "Biasa":
            saran.append("⛔ **DITOLAK (SNI 1726):** Untuk Kategori Desain Seismik D/E/F, WAJIB menggunakan SRPMK (Sistem Rangka Pemikul Momen Khusus) atau Dinding Geser.")
            
    return saran
