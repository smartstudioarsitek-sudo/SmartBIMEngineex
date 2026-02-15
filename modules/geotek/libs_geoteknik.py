import numpy as np
import matplotlib.pyplot as plt

class Geotech_Engine:
    def __init__(self, gamma_tanah=18, phi=30, c=10):
        self.gamma = gamma_tanah 
        self.phi = phi           
        self.c = c               
        
    def hitung_talud_batu_kali(self, H, b_atas, b_bawah, beban_atas_q=0):
        """
        Analisis Stabilitas Dinding Penahan Tanah (Batu Kali)
        """
        # 1. Tekanan Tanah Aktif (Rankine)
        # Konversi sudut phi ke radian
        Ka = np.tan(np.radians(45 - self.phi/2))**2
        
        # Gaya dorong tanah (Pa)
        Pa = 0.5 * self.gamma * (H**2) * Ka
        # Gaya akibat beban merata di atas (Pq)
        Pq = beban_atas_q * H * Ka
        
        Total_Dorong_H = Pa + Pq
        
        # Momen Guling (Overturning Moment)
        # Pa bekerja di H/3, Pq bekerja di H/2
        Momen_Guling = (Pa * H/3) + (Pq * H/2)
        
        # 2. Berat Sendiri Dinding (Gravity Wall)
        gamma_batu = 22.0 # kN/m3
        # Bagi jadi 2 bangun: Persegi panjang & Segitiga
        W1 = b_atas * H * gamma_batu # Bagian persegi
        W2 = 0.5 * (b_bawah - b_atas) * H * gamma_batu # Bagian segitiga
        Total_Berat_V = W1 + W2
        
        # Momen Tahan (Resisting Moment)
        # Lengan momen terhadap titik guling (ujung kaki depan)
        L1 = b_bawah - (b_atas / 2) 
        L2 = (b_bawah - b_atas) * (2/3) 
        Momen_Tahan = (W1 * L1) + (W2 * L2)
        
        # 3. Safety Factor (SF)
        # SF Guling
        SF_Guling = Momen_Tahan / Momen_Guling if Momen_Guling > 0 else 99.0
        
        # SF Geser
        # Gaya geser penahan = Berat * koefisien gesek (tan phi) + Kohesi * Lebar
        mu = np.tan(np.radians(2/3 * self.phi)) # Asumsi gesekan dasar
        Gaya_Geser_Tahan = (Total_Berat_V * mu) + (self.c * b_bawah)
        SF_Geser = Gaya_Geser_Tahan / Total_Dorong_H if Total_Dorong_H > 0 else 99.0
        
        # Koordinat untuk Visualisasi
        coords = [(0, 0), (b_bawah, 0), (b_bawah, H), (b_bawah - b_atas, H), (0, 0)]
        
        return {
            "SF_Guling": round(SF_Guling, 2),
            "SF_Geser": round(SF_Geser, 2),
            "Vol_Per_M": (b_atas + b_bawah)/2 * H,
            "Coords": coords,
            "Status": "AMAN" if SF_Guling >= 1.5 and SF_Geser >= 1.5 else "TIDAK AMAN"
        }

    # ===============================================
    # [WAJIB ADA] FUNGSI YANG DIPANGGIL ORKESTRA AI
    # ===============================================
    def daya_dukung_bore_pile(self, d, l, n_ujung, n_selimut):
        """
        Menghitung Daya Dukung Pondasi Bore Pile.
        Mengembalikan 4 nilai (qp, qs, q_ult, q_allow) sesuai format prompt Orkestra.
        
        Parameter:
        d = diameter (meter)
        l = kedalaman/panjang (meter)
        n_ujung = N-SPT di ujung tiang
        n_selimut = N-SPT rata-rata selimut tiang
        """
        # 1. Daya Dukung Ujung (End Bearing) - Metode Reese & Wright
        # Luas penampang tiang
        Ap = 0.25 * np.pi * (d**2)
        
        # Tahanan ujung (qp) dalam kN/m2
        # Rumus empiris: qp = 40 * N_SPT (batas maks 4000 kPa)
        qp_unit = min(40 * n_ujung * 10, 4000) # dikali 10 untuk konversi approx ton/m2 ke kN/m2
        Qp = qp_unit * Ap
        
        # 2. Daya Dukung Selimut (Friction)
        # Luas selimut tiang
        As = np.pi * d * l
        
        # Tahanan gesek (qs) dalam kN/m2
        # Rumus empiris: fs = 2.0 * N_SPT (approx untuk tanah campur lempung/pasir)
        fs_unit = 2.0 * n_selimut * 10 # dikali 10 konversi ke kN/m2
        Qs = fs_unit * As
        
        # 3. Total Ultimate & Allowable
        Q_ult = Qp + Qs
        SF = 2.5 # Safety Factor standar pondasi dalam
        Q_allow = Q_ult / SF
        
        # Return 4 values (sesuai permintaan prompt AI: qp, qs, q_ult, q_allow)
        return Qp, Qs, Q_ult, Q_allow

    # Alias untuk kompatibilitas jika dipanggil dengan nama lain
    def hitung_bore_pile(self, diameter_cm, kedalaman_m, N_spt_rata):
        """Fungsi pembungkus sederhana untuk input lama"""
        # Konversi input lama ke input baru
        d = diameter_cm / 100.0
        l = kedalaman_m
        n_ujung = N_spt_rata
        n_selimut = N_spt_rata
        
        Qp, Qs, Q_ult, Q_allow = self.daya_dukung_bore_pile(d, l, n_ujung, n_selimut)
        
        return {
            "Q_allow_kN": round(Q_allow, 2), 
            "Vol_Beton": 0.25 * np.pi * d**2 * l
        }
