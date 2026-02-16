import numpy as np

class SNI_Gempa_2019:
    def __init__(self, Ss, S1, Kelas_Situs):
        """
        Inisialisasi Perhitungan Gempa SNI 1726:2019.
        Input:
        - Ss: Percepatan batuan dasar periode pendek (g)
        - S1: Percepatan batuan dasar periode 1 detik (g)
        - Kelas_Situs: 'SA', 'SB', 'SC', 'SD', 'SE', atau 'SF'
        """
        # Konversi ke float untuk keamanan matematika
        self.Ss = float(Ss)
        self.S1 = float(S1)
        self.Site = Kelas_Situs
        
        # 1. Hitung Koefisien Situs dengan INTERPOLASI LINEAR (Bukan Step Function)
        self.Fa, self.Fv, self.Note = self.hitung_koefisien_interpolasi()
        
        # 2. Hitung Parameter Spektrum Desain (SDS & SD1)
        self.Sms = self.Fa * self.Ss
        self.Sm1 = self.Fv * self.S1
        self.Sds = (2/3) * self.Sms
        self.Sd1 = (2/3) * self.Sm1
        
        # 3. Hitung Periode Transisi (T0 dan Ts)
        # Menggunakan pengecekan agar tidak error pembagian nol (ZeroDivisionError)
        if self.Sds == 0:
            self.T0 = 0
            self.Ts = 0
        else:
            self.T0 = 0.2 * (self.Sd1 / self.Sds)
            self.Ts = self.Sd1 / self.Sds

    def hitung_koefisien_interpolasi(self):
        """
        Melakukan Interpolasi Linear untuk Tabel 6 & 7 SNI 1726:2019.
        Menggantikan logika 'Tangga' (Step Function) yang tidak akurat.
        """
        note = "Normal"
        
        # --- DATABASE TABEL SNI 1726:2019 ---
        # Header kolom untuk nilai Ss dan S1
        header_Ss = [0.25, 0.5, 0.75, 1.0, 1.25]
        header_S1 = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Tabel 6: Koefisien Fa
        table_Fa = {
            'SA': [0.8, 0.8, 0.8, 0.8, 0.8],
            'SB': [1.0, 1.0, 1.0, 1.0, 1.0],
            'SC': [1.2, 1.2, 1.1, 1.0, 1.0],
            'SD': [1.6, 1.4, 1.2, 1.1, 1.0],
            'SE': [2.5, 1.7, 1.2, 0.9, 0.9], 
            'SF': [None, None, None, None, None] # SS (Site Specific / Butuh Analisis Khusus)
        }
        
        # Tabel 7: Koefisien Fv
        table_Fv = {
            'SA': [0.8, 0.8, 0.8, 0.8, 0.8],
            'SB': [1.0, 1.0, 1.0, 1.0, 1.0],
            'SC': [1.7, 1.6, 1.5, 1.4, 1.3],
            'SD': [2.4, 2.0, 1.8, 1.6, 1.5],
            'SE': [3.5, 3.2, 2.8, 2.4, 2.4],
            'SF': [None, None, None, None, None]
        }

        # --- LOGIKA PENENTUAN Fa (INTERPOLASI) ---
        if self.Site == 'SF':
            return 0, 0, "BAHAYA: Kelas Situs SF Wajib Analisis Respon Spesifik!"
            
        # Ambil baris data berdasarkan situs (Default ke SD jika typo)
        vals_Fa = table_Fa.get(self.Site, table_Fa['SD']) 
        
        # Lakukan Interpolasi Linear menggunakan Numpy
        # np.interp(x, xp, fp) -> mencari nilai y pada posisi x
        Fa = np.interp(self.Ss, header_Ss, vals_Fa)
        
        # --- LOGIKA PENENTUAN Fv (INTERPOLASI) ---
        vals_Fv = table_Fv.get(self.Site, table_Fv['SD'])
        Fv = np.interp(self.S1, header_S1, vals_Fv)

        # --- VALIDASI KHUSUS TANAH LUNAK (SE) ---
        # Sesuai Pasal 6.10.1 SNI 1726:2019
        if self.Site == 'SE':
            if self.Ss >= 1.0:
                 note = "PERINGATAN (Pasal 6.10.1): Ss >= 1.0 di Tanah Lunak. Sebaiknya dilakukan Analisis Spesifik Situs."
            
            if self.S1 >= 0.2:
                # Ini peringatan kritikal dari audit
                note = "⛔ CRITICAL WARNING (SNI Pasal 6.10.1): S1 >= 0.2 pada Tanah Lunak (SE). SNI mewajibkan Analisis Respons Spesifik Situs! Nilai Fv ini hanya estimasi."

        return round(Fa, 3), round(Fv, 3), note

    def get_response_spectrum(self):
        """
        Helper untuk membuat data plotting grafik spektrum di Streamlit.
        Output: Tuple (List Periode T, List Percepatan Sa)
        """
        # Membuat array T dari 0 sampai 4 detik (100 titik data)
        T = np.linspace(0, 4, 100)
        Sa = []
        
        for t in T:
            if t < self.T0:
                # Fase Naik Linear
                val = self.Sds * (0.4 + 0.6 * t / self.T0)
            elif t < self.Ts:
                # Fase Plateau (Datar)
                val = self.Sds
            else:
                # Fase Turun (Hiperbolik 1/T)
                if t == 0: 
                    val = 0 
                else: 
                    val = self.Sd1 / t
            Sa.append(val)
            
        return T, Sa
