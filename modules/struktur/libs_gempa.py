import numpy as np

class SNI_Gempa_1726:
    def __init__(self, Ss, S1, Kelas_Situs):
        self.Ss = float(Ss)
        self.S1 = float(S1)
        self.Site = Kelas_Situs
        self.Fa, self.Fv = self.tentukan_koefisien_situs()
        
        self.Sms = self.Fa * self.Ss
        self.Sm1 = self.Fv * self.S1
        self.Sds = (2/3) * self.Sms
        self.Sd1 = (2/3) * self.Sm1
        
        # Periode Transisi
        if self.Sds > 0:
            self.T0 = 0.2 * (self.Sd1 / self.Sds)
            self.Ts = self.Sd1 / self.Sds
        else:
            self.T0 = 0; self.Ts = 0

    def tentukan_koefisien_situs(self):
        # Logika Sederhana Fa
        if self.Site == 'SE': Fa = 0.9 if self.Ss >= 1.0 else 2.5
        elif self.Site == 'SD': Fa = 1.1 if self.Ss >= 1.0 else 1.6
        else: Fa = 1.0
            
        # Logika Sederhana Fv
        if self.Site == 'SE': Fv = 2.4 if self.S1 >= 0.5 else 3.5
        elif self.Site == 'SD': Fv = 1.7 if self.S1 >= 0.5 else 2.4
        else: Fv = 1.0
            
        return Fa, Fv

    def hitung_base_shear(self, Berat_W_kN, R_redaman=8.0):
        Cs = self.Sds / (R_redaman / 1.0)
        V = Cs * Berat_W_kN
        return V, self.Sds, self.Sd1

    # ===============================================
    # [FIX] FUNGSI UTAMA & ALIAS BAHASA INGGRIS
    # ===============================================
    def get_respons_spektrum(self, T_max=4.0):
        """Fungsi Utama (Bahasa Indonesia)"""
        T_vals = np.linspace(0, T_max, 100)
        Sa_vals = []
        for T in T_vals:
            if T < self.T0: val = self.Sds * (0.4 + 0.6 * (T / self.T0))
            elif T <= self.Ts: val = self.Sds
            else: val = self.Sd1 / T if T > 0 else 0
            Sa_vals.append(val)
        return T_vals, np.array(Sa_vals)

    def get_response_spectrum_data(self, T_max=4.0):
        """
        [ALIAS] Wrapper Bahasa Inggris.
        Jaga-jaga kalau AI halusinasi pakai bahasa Inggris.
        """
        return self.get_respons_spektrum(T_max)
