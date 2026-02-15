import numpy as np
import math

class SNI_Concrete_2847:
    """
    Engine perhitungan Struktur Beton Bertulang berdasarkan SNI 2847:2019
    """
    def __init__(self, fc, fy):
        self.fc = fc # MPa
        self.fy = fy # MPa
        self.beta1 = 0.85 if fc <= 28 else max(0.85 - 0.05 * (fc - 28) / 7, 0.65)

    def hitung_momen_nominal(self, b, h, As, ds):
        """
        Menghitung Kapasitas Momen (Phi Mn) balok persegi.
        b, h, ds dalam mm. As dalam mm2.
        Output: Phi_Mn (kNm)
        """
        # Kedalaman blok tekan (a)
        # a = (As * fy) / (0.85 * fc * b)
        a = (As * self.fy) / (0.85 * self.fc * b)
        
        # Momen Nominal (Mn) -> Nmm
        # Mn = As * fy * (d - a/2)
        d = h - ds
        Mn = As * self.fy * (d - a / 2)
        
        # Faktor Reduksi Kekuatan (Phi) - SNI 2847 Tabel 21.2.1
        # Asumsi terkendali tarik (Tension Controlled) untuk balok
        phi = 0.9 
        
        return (phi * Mn) / 1e6 # Convert ke kNm

    def kebutuhan_tulangan(self, Mu_kNm, b, h, ds):
        """
        Desain Tulangan Perlu (As_req) berdasarkan Mu.
        """
        phi = 0.9
        d = h - ds
        Mu = Mu_kNm * 1e6 # Nmm
        
        # Rumus Pendekatan (Simplified Design)
        # As = Mu / (phi * fy * 0.875 * d)
        As_perlu = Mu / (phi * self.fy * 0.875 * d)
        
        # Cek Minimum Reinforcement (SNI 2847 Pasal 9.6.1.2)
        As_min1 = (0.25 * np.sqrt(self.fc) / self.fy) * b * d
        As_min2 = (1.4 / self.fy) * b * d
        As_min = max(As_min1, As_min2)
        
        return max(As_perlu, As_min)

class SNI_Load_1727:
    """
    Kombinasi Pembebanan SNI 1727:2020
    """
    @staticmethod
    def komb_pembebanan(D, L):
        """
        Mengembalikan Envelope beban terbesar (kNm atau kN)
        K1: 1.4D
        K2: 1.2D + 1.6L
        """
        k1 = 1.4 * D
        k2 = 1.2 * D + 1.6 * L
        return max(k1, k2)

class SNI_Concrete_2019:
    def __init__(self, fc, fy):
        self.fc = fc
        self.fy = fy

    def hitung_geser_beton_vc(self, bw, d, Av_terpasang=0, Nu=0, Ag=0):
        """
        Menghitung Kuat Geser Beton (Vc) sesuai SNI 2847:2019.
        Memperhitungkan Size Effect Factor (lambda_s).
        """
        # 1. Tentukan Lambda_s (Size Effect)
        # Jika ada tulangan geser (sengkang) memadai, lambda_s = 1.0
        # Jika tidak ada sengkang (plat/footing), lambda_s dihitung.
        if Av_terpasang > 0:
            lambda_s = 1.0
        else:
            # Rumus Size Effect: sqrt(2 / (1 + 0.004*d))
            lambda_s = math.sqrt(2.0 / (1.0 + 0.004 * d))
            if lambda_s > 1.0: lambda_s = 1.0
        
        # 2. Rumus Vc Baru (Tabel 22.5.5.1 SNI 2847:2019)
        # Vc = [0.66 * lambda_s * (rho_w)^(1/3) * sqrt(fc) + (Nu/6Ag)] * bw * d
        # Sederhananya untuk balok umum (rho_w dianggap min 0.015 untuk konservatif jika data kurang)
        
        # Versi Simplified (Konservatif & Aman):
        # 0.17 * lambda_s * sqrt(fc) * bw * d
        vc = 0.17 * lambda_s * math.sqrt(self.fc) * bw * d
        
        # Koreksi jika ada gaya aksial tekan (Nu) - Opsional
        if Nu > 0 and Ag > 0:
            vc += (Nu / (6 * Ag)) * bw * d
            
        return vc, lambda_s
