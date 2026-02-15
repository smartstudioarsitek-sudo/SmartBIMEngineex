import numpy as np
import matplotlib.pyplot as plt

class Geotech_Engine:
    # [FIX] INIT FLEXIBLE
    # Menerima 'gamma' ATAU 'gamma_tanah' agar AI tidak error
    def __init__(self, gamma=18, gamma_tanah=None, phi=30, c=10):
        # Logika prioritas: Jika 'gamma' diisi pakai itu, jika tidak pakai 'gamma_tanah', default 18
        if gamma is not None:
            self.gamma = gamma
        elif gamma_tanah is not None:
            self.gamma = gamma_tanah
        else:
            self.gamma = 18.0
            
        self.phi = phi           
        self.c = c               
        
    def hitung_talud_batu_kali(self, H, b_atas, b_bawah, beban_atas_q=0):
        # 1. Tekanan Tanah Aktif (Rankine)
        # Konversi phi ke radian
        phi_rad = np.radians(self.phi)
        Ka = np.tan(np.radians(45) - phi_rad/2)**2
        
        Pa = 0.5 * self.gamma * (H**2) * Ka
        Pq = beban_atas_q * H * Ka
        
        Total_Dorong_H = Pa + Pq
        Momen_Guling = (Pa * H/3) + (Pq * H/2)
        
        # 2. Berat Sendiri
        gamma_batu = 22.0
        W1 = b_atas * H * gamma_batu
        W2 = 0.5 * (b_bawah - b_atas) * H * gamma_batu
        
        # Momen Tahan 
        L1 = b_bawah - (b_atas / 2) 
        L2 = (b_bawah - b_atas) * (2/3) 
        Momen_Tahan = (W1 * L1) + (W2 * L2)
        
        # 3. SF
        SF_Guling = Momen_Tahan / Momen_Guling if Momen_Guling > 0 else 99.0
        
        return {
            "SF_Guling": round(SF_Guling, 2),
            "Status": "AMAN" if SF_Guling >= 1.5 else "BAHAYA"
        }

    # ===============================================
    # [FIX] FUNGSI BORE PILE (MULTI-ALIAS)
    # ===============================================
    def daya_dukung_bore_pile(self, d, l, n_ujung, n_selimut):
        """
        Fungsi Utama Hitung Bore Pile (4 Return Values)
        """
        # Luas
        Ap = 0.25 * np.pi * (d**2)
        As = np.pi * d * l
        
        # 1. Ujung (End Bearing)
        # qp max 4000 kPa (400 ton/m2)
        qp_val = min(40 * n_ujung, 400) * 10 # kN/m2
        Qp = qp_val * Ap
        
        # 2. Selimut (Friction)
        # fs = 2N (kN/m2) estimasi kasar
        fs_val = 2.0 * n_selimut * 10 
        Qs = fs_val * As
        
        # 3. Rekap
        Q_ult = Qp + Qs
        Q_allow = Q_ult / 2.5
        
        return Qp, Qs, Q_ult, Q_allow

    # ALIAS 1: Jika AI memanggil 'hitung_bore_pile'
    def hitung_bore_pile(self, diameter_cm=None, kedalaman_m=None, N_spt_rata=None, d=None, l=None, n_ujung=None, n_selimut=None):
        # Normalisasi input
        D = d if d else (diameter_cm/100 if diameter_cm else 0.6)
        L = l if l else (kedalaman_m if kedalaman_m else 10)
        Nu = n_ujung if n_ujung else (N_spt_rata if N_spt_rata else 10)
        Ns = n_selimut if n_selimut else (N_spt_rata if N_spt_rata else 10)
        
        Qp, Qs, Q_ult, Q_allow = self.daya_dukung_bore_pile(D, L, Nu, Ns)
        
        # Return dictionary jika dipanggil lewat fungsi lama
        return {
            "Q_allow_kN": round(Q_allow, 2),
            "Q_ultimate_kN": round(Q_ult, 2)
        }
