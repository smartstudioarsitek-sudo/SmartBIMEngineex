import numpy as np

class Geotech_Engine:
    def __init__(self, gamma_tanah=18, phi=30, c=10):
        self.gamma = gamma_tanah 
        self.phi = phi           
        self.c = c               
        
    def hitung_talud_batu_kali(self, H, b_atas, b_bawah, beban_atas_q=0):
        # 1. Tekanan Tanah Aktif (Rankine)
        Ka = np.tan(np.radians(45 - self.phi/2))**2
        Pa = 0.5 * self.gamma * (H**2) * Ka
        Momen_Guling = (Pa * H/3)
        
        # 2. Berat Sendiri
        gamma_batu = 22.0
        W_total = ((b_atas + b_bawah)/2) * H * gamma_batu
        
        # Momen Tahan 
        L_lengan = b_bawah / 2
        Momen_Tahan = W_total * L_lengan
        
        SF_Guling = Momen_Tahan / Momen_Guling if Momen_Guling > 0 else 99
        
        return {
            "SF_Guling": round(SF_Guling, 2),
            "Status": "AMAN" if SF_Guling >= 1.5 else "BAHAYA"
        }

    # ===============================================
    # [FIX] FUNGSI BORE PILE (DENGAN ALIAS)
    # ===============================================
    def hitung_bore_pile(self, diameter_cm=None, kedalaman_m=None, N_spt_rata=None, d=None, l=None, n_ujung=None, n_selimut=None):
        """
        Fungsi Bore Pile yang fleksibel. Bisa terima parameter lama atau baru.
        """
        # Normalisasi Parameter (Biar AI mau input gaya apa aja tetep masuk)
        Dia = diameter_cm if diameter_cm else (d * 100 if d else 60)
        Depth = kedalaman_m if kedalaman_m else (l if l else 10)
        N_val = N_spt_rata if N_spt_rata else (n_ujung if n_ujung else 10)
        
        D_m = Dia / 100.0
        Ap = 0.25 * np.pi * D_m**2
        Keliling = np.pi * D_m
        
        # Metode Reese & Wright Sederhana
        qp = min(40 * N_val, 400) * 10 # kN/m2
        Qp = qp * Ap
        
        fs = 2.0 * N_val # kN/m2 (untuk tanah lempung/pasir mix)
        Qs = fs * Keliling * Depth
        
        Q_ult = Qp + Qs
        Q_allow = Q_ult / 2.5 # SF 2.5
        
        # Return format Tuple jika diminta tuple, atau Dict jika diminta dict
        return Qp, Qs, Q_ult, Q_allow

    # ALIAS: Agar kalau AI panggil 'daya_dukung_bore_pile', dia lari ke fungsi di atas
    def daya_dukung_bore_pile(self, d, l, n_ujung, n_selimut):
        return self.hitung_bore_pile(d=d, l=l, n_ujung=n_ujung)
