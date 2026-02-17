import numpy as np
import pandas as pd

class SNI_Gempa_2019:
    """
    Modul Perhitungan Gempa sesuai SNI 1726:2019.
    Fitur Utama:
    1. Interpolasi Linear Presisi (Non-Step Function).
    2. Deteksi Tanah Lunak & Tanah Khusus.
    3. Validasi Geoteknik (Sanity Check).
    """
    
    def __init__(self, Ss, S1, Kelas_Situs):
        """
        Inisialisasi Parameter Gempa.
        
        Args:
            Ss (float): Percepatan batuan dasar periode pendek (g).
            S1 (float): Percepatan batuan dasar periode 1 detik (g).
            Kelas_Situs (str): Kode situs ('SA', 'SB', 'SC', 'SD', 'SE', 'SF').
        """
        # 1. Sanitasi Input (Cegah Crash akibat input string/None)
        try:
            self.Ss = float(Ss)
            self.S1 = float(S1)
        except (ValueError, TypeError):
            self.Ss = 0.0
            self.S1 = 0.0
            
        self.Site = str(Kelas_Situs).upper().strip()
        
        # 2. Hitung Koefisien Situs (Fa & Fv) dengan INTERPOLASI LINEAR
        self.Fa, self.Fv, self.Note = self.hitung_koefisien_interpolasi()
        
        # 3. Hitung Parameter Spektrum Desain (SDS & SD1)
        # Rumus: SMS = Fa * Ss, SM1 = Fv * S1
        # Rumus: SDS = 2/3 * SMS, SD1 = 2/3 * SM1
        self.Sms = self.Fa * self.Ss
        self.Sm1 = self.Fv * self.S1
        self.Sds = (2/3) * self.Sms
        self.Sd1 = (2/3) * self.Sm1
        
        # 4. Hitung Periode Transisi (T0 dan Ts)
        # T0 = 0.2 * (SD1 / SDS)
        # Ts = SD1 / SDS
        if self.Sds > 0:
            self.T0 = 0.2 * (self.Sd1 / self.Sds)
            self.Ts = self.Sd1 / self.Sds
        else:
            self.T0 = 0.0
            self.Ts = 0.0

    def hitung_koefisien_interpolasi(self):
        """
        [CORE ALGORITHM]
        Melakukan Interpolasi Linear untuk Tabel 6 & 7 SNI 1726:2019.
        Menggantikan logika 'Tangga' (Step Function) yang dilarang auditor.
        """
        note = "Normal"
        
        # --- A. DATABASE TABEL SNI 1726:2019 ---
        # Header kolom untuk nilai Ss dan S1
        header_Ss = [0.25, 0.5, 0.75, 1.0, 1.25]
        header_S1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Tabel 6: Koefisien Fa (Amplifikasi Periode Pendek)
        table_Fa = {
            'SA': [0.8, 0.8, 0.8, 0.8, 0.8],
            'SB': [1.0, 1.0, 1.0, 1.0, 1.0],
            'SC': [1.2, 1.2, 1.1, 1.0, 1.0],
            'SD': [1.6, 1.4, 1.2, 1.1, 1.0],
            'SE': [2.5, 1.7, 1.2, 0.9, 0.9], 
            'SF': [None, None, None, None, None] # SS (Site Specific / Butuh Analisis Khusus)
        }
        
        # Tabel 7: Koefisien Fv (Amplifikasi Periode 1 Detik)
        table_Fv = {
            'SA': [0.8, 0.8, 0.8, 0.8, 0.8],
            'SB': [1.0, 1.0, 1.0, 1.0, 1.0],
            'SC': [1.7, 1.6, 1.5, 1.4, 1.3],
            'SD': [2.4, 2.0, 1.8, 1.6, 1.5],
            'SE': [3.5, 3.2, 2.8, 2.4, 2.4],
            'SF': [None, None, None, None, None]
        }

        # --- B. VALIDASI KELAS SITUS ---
        # Jika user memilih SF (Tanah Khusus), aplikasi wajib menolak hitungan.
        if self.Site == 'SF':
            return 0.0, 0.0, "⛔ BAHAYA: Kelas Situs SF (Tanah Khusus/Likuifaksi) mewajibkan Analisis Respons Spesifik Situs. Perhitungan otomatis tidak diizinkan."
            
        # Default ke SD jika input user tidak dikenali
        if self.Site not in table_Fa:
            self.Site = 'SD'
            note = "Info: Kelas Situs tidak dikenali, default ke SD."

        # --- C. ALGORITMA INTERPOLASI (NUMPY INTERP) ---
        # Ambil baris data berdasarkan situs
        vals_Fa = table_Fa[self.Site]
        vals_Fv = table_Fv[self.Site]
        
        # Interpolasi Fa (Ss)
        # np.interp otomatis menangani linear interpolation y = y1 + (x-x1)...
        # dan juga menangani clamping (batas atas/bawah)
        Fa = np.interp(self.Ss, header_Ss, vals_Fa)
        
        # Interpolasi Fv (S1)
        Fv = np.interp(self.S1, header_S1, vals_Fv)

        # --- D. PERINGATAN GEOTEKNIK (AUDIT COMPLIANCE) ---
        # Pasal 6.10.1: Peringatan untuk Tanah Lunak (SE)
        if self.Site == 'SE':
            if self.Ss >= 1.0:
                 note = "⚠️ WARNING: Ss >= 1.0 di Tanah Lunak. Sebaiknya dilakukan Analisis Spesifik Situs."
            
            if self.S1 >= 0.2:
                # Ini adalah syarat mutlak Audit Forensik
                note = "⛔ CRITICAL WARNING (SNI Pasal 6.10.1): S1 >= 0.2 pada Tanah Lunak (SE). SNI mewajibkan Analisis Respons Spesifik Situs! Nilai Fv ini hanya estimasi awal."

        return round(Fa, 3), round(Fv, 3), note

    def get_response_spectrum(self):
        """
        Helper untuk membuat data plotting grafik spektrum di Streamlit.
        Output: Tuple (List Periode T, List Percepatan Sa)
        """
        # Membuat array T dari 0 sampai 4 detik (100 titik data)
        # Menggunakan numpy linspace untuk presisi grafik
        T = np.linspace(0, 4, 100)
        Sa = []
        
        for t in T:
            if t < self.T0:
                # Fase Naik Linear (0 s/d T0)
                val = self.Sds * (0.4 + 0.6 * t / self.T0)
            elif t < self.Ts:
                # Fase Plateau / Datar (T0 s/d Ts)
                val = self.Sds
            else:
                # Fase Turun Hiperbolik (Ts s/d 4 detik)
                # Formula: Sa = SD1 / T
                if t == 0: 
                    val = 0 
                else: 
                    val = self.Sd1 / t
            Sa.append(val)
            
        return T, Sa

    @staticmethod
    def cek_kewajaran_tanah(kelas_situs, n_spt, vs30=None, su=None):
        """
        [FITUR BARU - AUDIT FORENSIK]
        Memvalidasi apakah kombinasi parameter tanah masuk akal.
        Mencegah user input 'Mustahil' (Misal: N-SPT=2 tapi pilih Tanah Keras).
        
        Args:
            kelas_situs (str): SA, SB, SC, SD, SE.
            n_spt (float): Nilai N-SPT rata-rata.
            vs30 (float): Kecepatan gelombang geser (opsional).
            su (float): Kuat geser niralir (opsional).
            
        Returns:
            bool: True jika wajar, False jika mencurigakan.
            str: Pesan error/validasi.
        """
        site = kelas_situs.upper()
        msg = "Data Valid."
        valid = True
        
        # Logika Validasi Sederhana N-SPT (Tabel 3 SNI 1726:2019)
        if n_spt is not None:
            n = float(n_spt)
            
            # Cek Tanah Keras (SC) -> N harus > 50
            if site == 'SC' and n < 50:
                return False, f"❌ DATA TIDAK KONSISTEN: Anda memilih Kelas Situs SC (Tanah Keras), tapi N-SPT = {n} (< 50). Harusnya masuk SD atau SE."
            
            # Cek Tanah Sedang (SD) -> N antara 15 s/d 50
            if site == 'SD' and (n < 15 or n > 50):
                return False, f"❌ DATA TIDAK KONSISTEN: Anda memilih Kelas Situs SD (Tanah Sedang), tapi N-SPT = {n}. SD mensyaratkan 15 < N < 50."
            
            # Cek Tanah Lunak (SE) -> N < 15
            if site == 'SE' and n >= 15:
                return False, f"❌ DATA TIDAK KONSISTEN: Anda memilih Kelas Situs SE (Tanah Lunak), tapi N-SPT = {n} (> 15). Kemungkinan ini Tanah Sedang (SD)."

        # Validasi Vs30 (Jika ada data)
        if vs30 is not None:
            v = float(vs30)
            if site == 'SA' and v < 1500:
                 return False, f"❌ DATA TIDAK KONSISTEN: Situs SA (Batuan Keras) wajib Vs30 > 1500 m/s. Data Anda: {v}."
            if site == 'SE' and v > 175:
                 return False, f"❌ DATA TIDAK KONSISTEN: Situs SE (Tanah Lunak) wajib Vs30 < 175 m/s. Data Anda: {v}."

        return True, "✅ Data Tanah Konsisten dengan Kelas Situs."

def generate_response_spectrum(Ss, S1, SiteClass='SD'):
    """
    Menghitung Parameter Gempa & Titik Kurva Respon Spektrum (SNI 1726:2019)
    Output: DataFrame (T, Sa) untuk di-plot di Streamlit.
    """
    # 1. Tentukan Fa & Fv (Tabel Klasifikasi Tanah - Simplified Logic)
    # [CATATAN: Idealnya ini database lengkap, ini versi simplifikasi SD Tanah Sedang]
    Fa = 1.2 # Asumsi SD
    Fv = 1.5 # Asumsi SD
    
    # 2. Hitung Parameter Desain (SMS, SM1, SDS, SD1)
    SMS = Fa * Ss
    SM1 = Fv * S1
    SDS = (2/3) * SMS
    SD1 = (2/3) * SM1
    
    # 3. Hitung Perioda Batas (T0 & Ts)
    T0 = 0.2 * (SD1 / SDS)
    Ts = SD1 / SDS
    
    # 4. Generate Titik Kurva (T vs Sa)
    T_axis = np.linspace(0, 4.0, 100) # 0 sampai 4 detik
    Sa_axis = []
    
    for T in T_axis:
        if T < T0:
            val = SDS * (0.4 + 0.6 * (T / T0))
        elif T >= T0 and T <= Ts:
            val = SDS
        elif T > Ts:
            val = SD1 / T
        Sa_axis.append(val)
        
    df_spectrum = pd.DataFrame({'Period (T)': T_axis, 'Accel (Sa)': Sa_axis})
    
    # Return Dataframe dan Parameter Kunci untuk Laporan
    params = {'SDS': SDS, 'SD1': SD1, 'T0': T0, 'Ts': Ts}
    return df_spectrum, params
