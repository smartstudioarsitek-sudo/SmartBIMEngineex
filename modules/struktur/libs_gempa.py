import numpy as np

class SNI_Gempa_1726:
    def __init__(self, Ss, S1, Kelas_Situs):
        self.Ss = Ss
        self.S1 = S1
        self.Site = Kelas_Situs
        self.Fa, self.Fv = self.tentukan_koefisien_situs()
        
        # Hitung Parameter Desain (SDS, SD1)
        self.Sms = self.Fa * self.Ss
        self.Sm1 = self.Fv * self.S1
        self.Sds = (2/3) * self.Sms
        self.Sd1 = (2/3) * self.Sm1
        
        # Hitung Periode Transisi (T0, Ts)
        self.T0 = 0.2 * (self.Sd1 / self.Sds) if self.Sds > 0 else 0
        self.Ts = self.Sd1 / self.Sds if self.Sds > 0 else 0

    def tentukan_koefisien_situs(self):
        # Tabel Sederhana SNI 1726
        # Fa
        if self.Site == 'SE': # Tanah Lunak
            Fa = 0.9 if self.Ss >= 1.0 else (1.2 if self.Ss >= 0.75 else 2.5)
        elif self.Site == 'SD': # Tanah Sedang
            Fa = 1.1 if self.Ss >= 1.0 else (1.2 if self.Ss >= 0.75 else 1.6)
        else: Fa = 1.0
            
        # Fv
        if self.Site == 'SE':
            Fv = 2.4 if self.S1 >= 0.5 else (2.8 if self.S1 >= 0.4 else 3.5)
        elif self.Site == 'SD':
            Fv = 1.7 if self.S1 >= 0.5 else (1.9 if self.S1 >= 0.4 else 2.4)
        else: Fv = 1.0
            
        return Fa, Fv

    def hitung_base_shear(self, Berat_W_kN, R_redaman):
        # Gaya Geser Dasar (V)
        Cs = self.Sds / (R_redaman / 1.0)
        V = Cs * Berat_W_kN
        return V, self.Sds, self.Sd1

    # ===============================================
    # [FITUR BARU] UNTUK MEMBUAT GRAFIK GEMPA
    # ===============================================
    def get_respons_spektrum(self, T_max=4.0):
        """
        Menghasilkan data kurva (X, Y) untuk plot grafik respons spektrum.
        """
        T_vals = np.linspace(0, T_max, 100)
        Sa_vals = []
        
        for T in T_vals:
            if T < self.T0:
                # Fase Naik Linear
                val = self.Sds * (0.4 + 0.6 * (T / self.T0))
            elif T <= self.Ts:
                # Fase Datar (Plateau)
                val = self.Sds
            else:
                # Fase Menurun (Decay)
                val = self.Sd1 / T if T > 0 else 0
            
            Sa_vals.append(val)
            
        return T_vals, np.array(Sa_vals)
