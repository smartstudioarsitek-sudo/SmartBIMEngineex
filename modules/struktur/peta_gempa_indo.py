# modules/struktur/peta_gempa_indo.py

def get_data_kota():
    """
    Database Sederhana Parameter Gempa Wilayah Indonesia (SNI 1726:2019).
    Nilai Ss (Short Period) dan S1 (1-Second Period) untuk Tanah Batuan (SB).
    """
    database = {
        "Aceh - Banda Aceh": {"Ss": 1.45, "S1": 0.60},
        "Sumut - Medan": {"Ss": 0.90, "S1": 0.40},
        "Sumbar - Padang": {"Ss": 1.50, "S1": 0.65},
        "Riau - Pekanbaru": {"Ss": 0.25, "S1": 0.15},
        "Kepri - Batam": {"Ss": 0.18, "S1": 0.10},
        "Jambi - Jambi": {"Ss": 0.30, "S1": 0.20},
        "Sumsel - Palembang": {"Ss": 0.35, "S1": 0.25},
        "Lampung - Bandar Lampung": {"Ss": 1.10, "S1": 0.45},
        "Bengkulu - Bengkulu": {"Ss": 1.30, "S1": 0.60},
        "DKI Jakarta": {"Ss": 0.75, "S1": 0.35},
        "Jabar - Bandung": {"Ss": 1.10, "S1": 0.50},
        "Jateng - Semarang": {"Ss": 0.80, "S1": 0.35},
        "DIY - Yogyakarta": {"Ss": 1.25, "S1": 0.55},
        "Jatim - Surabaya": {"Ss": 0.65, "S1": 0.30},
        "Bali - Denpasar": {"Ss": 1.05, "S1": 0.45},
        "Kaltim - IKN (Nusantara)": {"Ss": 0.20, "S1": 0.10}, # Zona Aman
        "Sulsel - Makassar": {"Ss": 0.40, "S1": 0.20},
        "Sulteng - Palu": {"Ss": 1.60, "S1": 0.70}, # Zona Merah
        "Papua - Jayapura": {"Ss": 1.55, "S1": 0.65},
    }
    return database

def hitung_respon_spektrum(Ss, S1, kelas_situs='SE'):
    """
    Menghitung Parameter Desain (SDS, SD1) berdasarkan Kelas Situs Tanah.
    Input:
    - Ss, S1: Parameter batuan dasar
    - kelas_situs: SA (Keras) s/d SE (Lunak)
    """
    # 1. Tentukan Fa dan Fv (Faktor Amplifikasi) - Tabel SNI Sederhana
    # (Implementasi logika tabel Fa Fv yang panjang disederhanakan untuk MVP)
    
    # Default untuk Tanah Lunak (SE) - Kondisi paling umum/kritis di proyek gedung
    if kelas_situs == 'SE':
        # Tabel Fa (Interpolasi kasar)
        if Ss <= 0.25: Fa = 2.5
        elif Ss <= 0.50: Fa = 1.7
        elif Ss <= 0.75: Fa = 1.2
        elif Ss <= 1.00: Fa = 0.9
        else: Fa = 0.9
        
        # Tabel Fv
        if S1 <= 0.1: Fv = 3.5
        elif S1 <= 0.2: Fv = 3.2
        elif S1 <= 0.3: Fv = 2.8
        elif S1 <= 0.4: Fv = 2.4
        elif S1 >= 0.5: Fv = 2.4
        else: Fv = 2.4
    else:
        # Default aman (tanah sedang SD)
        Fa, Fv = 1.2, 1.5 

    # 2. Hitung SMS dan SM1
    SMS = Fa * Ss
    SM1 = Fv * S1
    
    # 3. Hitung SDS dan SD1 (Parameter Desain)
    SDS = (2/3) * SMS
    SD1 = (2/3) * SM1
    
    # 4. Tentukan Kategori Desain Seismik (KDS)
    if SDS < 0.167: kds = 'A'
    elif SDS < 0.33: kds = 'B'
    elif SDS < 0.50: kds = 'C'
    else: kds = 'D' # D bisa D, E, atau F tergantung S1 juga
    
    return SDS, SD1, kds
