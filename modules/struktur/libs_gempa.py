import numpy as np

class SNI_Gempa_1726:
    def __init__(self, Ss, S1, Kelas_Situs):
        """
        Inisialisasi Parameter Gempa SNI 1726:2019
        """
        self.Ss = float(Ss)
        self.S1 = float(S1)
        self.Site = Kelas_Situs
        
        # 1. Tentukan Koefisien Situs (Fa, Fv) otomatis
        self.Fa, self.Fv = self.tentukan_koefisien_situs()
        
        # 2. Hitung Parameter Percepatan Desain (SDS, SD1)
        self.Sms = self.Fa * self.Ss
        self.Sm1 = self.Fv * self.S1
        self.Sds = (2/3) * self.Sms
        self.Sd1 = (2/3) * self.Sm1
        
        # 3. Hitung Periode Transisi (T0 dan Ts) untuk Grafik
        # Hindari pembagian dengan nol
        if self.Sds > 0:
            self.T0 = 0.2 * (self.Sd1 / self.Sds)
            self.Ts = self.Sd1 / self.Sds
        else:
            self.T0 = 0
            self.Ts = 0

    def tentukan_koefisien_situs(self):
        """
        Menentukan Fa dan Fv berdasarkan Kelas Situs (SE/SD/SC) dan nilai Ss/S1.
        Mengacu pada Tabel SNI 1726:2019.
        """
        # --- Menentukan Fa ---
        if self.Site == 'SE': # Tanah Lunak
            if self.Ss <= 0.25: Fa = 2.5
            elif self.Ss <= 0.5: Fa = 1.7
            elif self.Ss <= 0.75: Fa = 1.2
            elif self.Ss >= 1.0: Fa = 0.9
            else: Fa = 1.2 # Interpolasi kasar
            
        elif self.Site == 'SD': # Tanah Sedang
            if self.Ss <= 0.25: Fa = 1.6
            elif self.Ss <= 0.5: Fa = 1.4
            elif self.Ss <= 0.75: Fa = 1.2
            elif self.Ss >= 1.0: Fa = 1.1
            else: Fa = 1.2
            
        elif self.Site == 'SC': # Tanah Keras
            if self.Ss <= 0.25: Fa = 1.2
            elif self.Ss >= 1.0: Fa = 1.0
            else: Fa = 1.1
            
        else: # Default (SB/SA)
            Fa = 1.0

        # --- Menentukan Fv ---
        if self.Site == 'SE': # Tanah Lunak
            if self.S1 <= 0.1: Fv = 3.5
            elif self.S1 <= 0.2: Fv = 3.2
            elif self.S1 <= 0.4: Fv = 2.4
            elif self.S1 >= 0.5: Fv = 2.4
            else: Fv = 2.8
            
        elif self.Site == 'SD': # Tanah Sedang
            if self.S1 <= 0.1: Fv = 2.4
            elif self.S1 <= 0.2: Fv = 2.0
            elif self.S1 <= 0.4: Fv = 1.6
            elif self.S1 >= 0.5: Fv = 1.7
            else: Fv = 1.8
            
        elif self.Site == 'SC': # Tanah Keras
            if self.S1 <= 0.1: Fv = 1.7
            elif self.S1 >= 0.5: Fv = 1.3
            else: Fv = 1.5
            
        else: # Default
            Fv = 1.0
            
        return Fa, Fv

    def hitung_base_shear(self, Berat_W_kN, R_redaman=8.0, Ie=1.0):
        """
        Menghitung Gaya Geser Dasar Seismik (V)
        """
        # Koefisien Respons Seismik (Cs)
        if R_redaman == 0: R_redaman = 1
        
        Cs = self.Sds / (R_redaman / Ie)
        
        # Batas Atas Cs (Cs Max)
        # Asumsi T hitungan perioda struktur sekitar 1 detik untuk gedung tinggi
        T_asumsi = 1.0 
        if T_asumsi <= self.Ts:
            Cs_max = self.Sds
        else:
            Cs_max = self.Sd1 / (T_asumsi * (R_redaman / Ie))
            
        Cs = min(Cs, Cs_max)
        
        # Gaya Geser Dasar
        V = Cs * Berat_W_kN
        return V, self.Sds, self.Sd1

    # ===============================================
    # [WAJIB ADA] UNTUK GRAFIK ORKESTRA AI
    # ===============================================
    def get_respons_spektrum(self, T_max=4.0):
        """
        Menghasilkan array T (periode) dan Sa (akselerasi) 
        untuk di-plot oleh matplotlib.
        """
        # Buat 100 titik data dari T=0 sampai T=4 detik
        T_vals = np.linspace(0, T_max, 100)
        Sa_vals = []
        
        for T in T_vals:
            if T < self.T0:
                # Fase Naik Linear (0 s/d T0)
                val = self.Sds * (0.4 + 0.6 * (T / self.T0))
            elif T <= self.Ts:
                # Fase Datar / Plateau (T0 s/d Ts)
                val = self.Sds
            else:
                # Fase Turun / Decay ( > Ts)
                # Rumus: Sd1 / T
                val = self.Sd1 / T if T > 0 else 0
            
            Sa_vals.append(val)
            
        return T_vals, np.array(Sa_vals)
