# modules/struktur/peta_gempa_indo.py

def get_data_kota():
    """
    Database Parameter Gempa Wilayah Indonesia (SNI 1726:2019).
    Nilai Ss (Short Period) dan S1 (1-Second Period) untuk Tanah Batuan (SB).
    """
    # Format: "Nama Kota": {"Ss": nilai, "S1": nilai}
    database = {
        "Pilih Manual": {"Ss": 0.0, "S1": 0.0},
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
        "Jateng - Solo": {"Ss": 0.90, "S1": 0.40},
        "DIY - Yogyakarta": {"Ss": 1.25, "S1": 0.55},
        "Jatim - Surabaya": {"Ss": 0.65, "S1": 0.30},
        "Jatim - Malang": {"Ss": 0.80, "S1": 0.40},
        "Bali - Denpasar": {"Ss": 1.05, "S1": 0.45},
        "NTB - Mataram": {"Ss": 1.15, "S1": 0.50},
        "NTT - Kupang": {"Ss": 0.90, "S1": 0.35},
        "Kalbar - Pontianak": {"Ss": 0.15, "S1": 0.10},
        "Kaltim - IKN (Nusantara)": {"Ss": 0.20, "S1": 0.10}, 
        "Kalsel - Banjarmasin": {"Ss": 0.10, "S1": 0.05},
        "Sulsel - Makassar": {"Ss": 0.40, "S1": 0.20},
        "Sulteng - Palu": {"Ss": 1.60, "S1": 0.70}, 
        "Sulut - Manado": {"Ss": 1.05, "S1": 0.45},
        "Maluku - Ambon": {"Ss": 1.00, "S1": 0.40},
        "Papua - Jayapura": {"Ss": 1.55, "S1": 0.65},
        "Papua - Merauke": {"Ss": 0.20, "S1": 0.10},
    }
    return database

def hitung_respon_spektrum(Ss, S1, kelas_situs):
    """
    Menghitung Parameter Desain (SDS, SD1) otomatis.
    """
    # 1. Tabel Faktor Amplifikasi Fa (Tabel 6 SNI 1726:2019)
    # Kelas Situs: SA(Batuan Keras) s/d SE(Tanah Lunak)
    
    # Logic Fa Sederhana (Interpolasi Linear pendekatan)
    def get_Fa(Ss, site):
        if site == 'SA': return 0.8
        if site == 'SB': return 1.0
        if site == 'SC': # Tanah Keras
            if Ss <= 0.25: return 1.2
            if Ss >= 1.0: return 1.0
            return 1.2 - ((Ss-0.25)/0.75)*0.2
        if site == 'SD': # Tanah Sedang
            if Ss <= 0.25: return 1.6
            if Ss >= 1.0: return 1.1 # Revisi SNI 2019 (sebelumnya 1.0)
            return 1.6 - ((Ss-0.25)/0.75)*0.5
        if site == 'SE': # Tanah Lunak
            if Ss <= 0.25: return 2.5
            if Ss >= 1.0: return 0.9
            return 2.5 - ((Ss-0.25)/0.75)*1.6
        return 1.0

    # Logic Fv Sederhana
    def get_Fv(S1, site):
        if site == 'SA': return 0.8
        if site == 'SB': return 1.0
        if site == 'SC':
            if S1 <= 0.1: return 1.7
            if S1 >= 0.5: return 1.3
            return 1.7 - ((S1-0.1)/0.4)*0.4
        if site == 'SD':
            if S1 <= 0.1: return 2.4
            if S1 >= 0.5: return 1.5 # Perhatikan Pasal Keruntuhan
            return 2.4 - ((S1-0.1)/0.4)*0.9
        if site == 'SE':
            if S1 <= 0.1: return 3.5
            if S1 >= 0.5: return 2.4
            return 3.5 - ((S1-0.1)/0.4)*1.1
        return 1.0

    Fa = get_Fa(Ss, kelas_situs)
    Fv = get_Fv(S1, kelas_situs)

    # 2. Hitung Parameter Respons Spektral
    SMS = Fa * Ss
    SM1 = Fv * S1
    SDS = (2/3) * SMS
    SD1 = (2/3) * SM1
    
    # 3. Periode Transisi (T0 dan Ts)
    T0 = 0.2 * (SD1 / SDS) if SDS > 0 else 0
    Ts = SD1 / SDS if SDS > 0 else 0
    
    return {
        "Fa": Fa, "Fv": Fv, 
        "SMS": SMS, "SM1": SM1, 
        "SDS": SDS, "SD1": SD1,
        "T0": T0, "Ts": Ts
    }
