import numpy as np
import pandas as pd
import math
from scipy.stats import gumbel_r, pearson3

class Hidrologi_Engine:
    """
    Engine Terpadu untuk Analisis Hidrologi:
    1. Klimatologi (Penman Modifikasi KP-01)
    2. Curah Hujan Rancangan (Statistik)
    3. Ketersediaan Air (FJ Mock)
    """
    
    def __init__(self):
        pass

    # =========================================
    # 1. KLIMATOLOGI (PENMAN MODIFIKASI)
    # =========================================
    def hitung_eto_penman(self, t_mean, rh_mean, sun_pct, u_ms, letak_lintang, elevasi, bulan_idx):
        """
        Hitung ETo Harian (mm/hari) metode Penman Modifikasi (Standar KP-01).
        """
        # 1. Data Uap Air
        # ea (Tekanan uap jenuh - mbar)
        ea = 6.11 * math.exp((17.27 * t_mean) / (t_mean + 237.3))
        # ed (Tekanan uap aktual - mbar)
        ed = ea * (rh_mean / 100)
        
        # 2. Fungsi Angin f(u) = 0.27 (1 + 0.864 * u)
        fu = 0.27 * (1 + 0.864 * u_ms)
        
        # 3. Radiasi (Ra) - Tabel Angstrom untuk Indonesia (Lintang -5 s/d -8 LS)
        # Angka rata-rata Ra harian per bulan (Jan - Des)
        ra_table = [15.1, 15.4, 15.2, 14.5, 13.6, 13.1, 13.4, 14.2, 15.0, 15.4, 15.3, 15.0]
        # Ambil Ra berdasarkan indeks bulan (0=Jan, 11=Des)
        Ra = ra_table[bulan_idx % 12]
        
        # Rs (Radiasi Gelombang Pendek) -> Rs = (0.25 + 0.54 * n/N) * Ra
        Rs = (0.25 + 0.54 * (sun_pct / 100)) * Ra
        
        # Rn (Radiasi Bersih)
        # Rns (Net Shortwave) - Albedo 0.25 (Tanaman Acuan/Rumput)
        Rns = 0.75 * Rs
        
        # Rnl (Net Longwave)
        # f(T) = sigma * T^4 (Approximation)
        ft = 2.043e-10 * ((t_mean + 273.16)**4)
        fed = 0.34 - 0.044 * math.sqrt(ed)
        fsun = 0.1 + 0.9 * (sun_pct / 100)
        Rnl = ft * fed * fsun
        
        Rn = Rns - Rnl
        
        # 4. Faktor Pembobot (W)
        # Delta (Kemiringan kurva tekanan uap)
        delta = 4098 * (0.6108 * math.exp(17.27 * t_mean / (t_mean + 237.3))) / ((t_mean + 237.3)**2)
        # Gamma (Konstanta Psikrometrik) - Koreksi Elevasi
        P = 101.3 * ((293 - 0.0065 * elevasi) / 293)**5.26
        gamma = 0.665e-3 * P * 10 # *10 agar satuan mbar match
        
        W = delta / (delta + gamma)
        
        # 5. ETo Final -> ETo = c * [W.Rn + (1-W).f(u).(ea-ed)]
        c = 0.90 # Faktor koreksi Indonesia (KP-01) untuk daerah sedang
        ETo = c * (W * Rn + (1 - W) * fu * (ea - ed))
        
        return max(0.0, round(ETo, 2))

    # =========================================
    # 2. STATISTIK BANJIR (GUMBEL & LOG PEARSON)
    # =========================================
    def analisis_frekuensi_hujan(self, data_hujan_max):
        """
        Input: List data hujan harian maksimum tahunan (minimal 2 data).
        Output: Dictionary statistik dan prediksi hujan rencana.
        """
        arr = np.array(data_hujan_max)
        n = len(arr)
        
        if n < 2:
            return {"Error": "Data kurang, minimal 2 tahun data."}
        
        # Statistik Dasar
        mu = np.mean(arr)
        std = np.std(arr, ddof=1)
        Cs = pd.Series(arr).skew()
        Ck = pd.Series(arr).kurt() + 3
        
        # --- Metode Gumbel ---
        # Reduced Mean (yn) & Reduced Std Dev (sn) - Simplifikasi tabel
        # Untuk n antara 10-100, kita pakai pendekatan regresi linear sederhana
        yn = 0.4952 + (0.0006 * n) # Aproksimasi
        sn = 0.9496 + (0.0025 * n) # Aproksimasi
        
        periods = [2, 5, 10, 25, 50, 100]
        hasil_gumbel = {}
        
        for T in periods:
            prob = 1 - (1/T)
            # Reduced variate (yt)
            yt = -math.log(-math.log(prob))
            # Faktor frekuensi (K)
            K = (yt - yn) / sn
            Xt = mu + (K * std)
            hasil_gumbel[f"R{T}"] = round(Xt, 1)
            
        return {
            "Statistik": {
                "Rata_rata": round(mu, 2),
                "Std_Dev": round(std, 2),
                "Skewness_Cs": round(Cs, 3),
                "Kurtosis_Ck": round(Ck, 3)
            },
            "Hujan_Rencana_Gumbel": hasil_gumbel
        }

    # =========================================
    # 3. KETERSEDIAAN AIR (FJ MOCK)
    # =========================================
    def simulasi_fj_mock(self, hujan_bulanan_mm, eto_bulanan_mm_hari, luas_das_km2):
        """
        Simulasi Debit Andalan Bulanan (Simplified FJ Mock).
        Input: List Hujan (12 bln), List ETo (12 bln), Luas DAS.
        """
        hasil_debit = []
        V_storage = 100.0 # Initial Soil Moisture Capacity (mm) - Asumsi awal
        SMC_max = 200.0 # Soil Moisture Capacity Max (mm)
        Infiltration_Coeff = 0.4 # Faktor Infiltrasi (0-1)
        Recession_Factor = 0.6 # Faktor Resesi Air Tanah
        
        # Loop 12 Bulan
        for i in range(12):
            R = hujan_bulanan_mm[i]
            # ETo harian * 30 hari = ETo Bulanan
            Et_pot = eto_bulanan_mm_hari[i] * 30.0 
            
            # Limited Evapotranspiration (Et_act)
            # Asumsi: Jika hujan > Et_pot, Et_act = Et_pot. Jika kering, Et_act turun.
            Et_act = Et_pot if R > Et_pot else R + (Et_pot - R) * 0.5
            
            WS = R - Et_act # Water Surplus
            
            # Soil Storage Balance
            V_new = V_storage + WS
            if V_new < 0: V_new = 0
            if V_new > SMC_max: V_new = SMC_max
            
            dV = V_new - V_storage # Perubahan tampungan
            V_storage = V_new # Update untuk bulan depan
            
            # Water Surplus Net
            WS_net = max(0, WS - dV)
            
            # Baseflow & Direct Runoff
            Baseflow = WS_net * Infiltration_Coeff
            DirectRunoff = WS_net - Baseflow
            
            # Total Runoff (mm/bulan)
            Total_RO_mm = Baseflow + DirectRunoff + (V_storage * 0.05 * Recession_Factor)
            
            # Konversi mm/bulan ke m3/s
            # Q = (RO_mm * 10^-3 * Area_km2 * 10^6) / (30 * 86400)
            Q_m3s = (Total_RO_mm * 1000 * luas_das_km2) / (30 * 86400)
            hasil_debit.append(max(0, Q_m3s))
            
        # Hitung Q80 (Debit Andalan Probabilitas 80%)
        # Urutkan dari besar ke kecil, ambil rank 80%
        q_sorted = sorted(hasil_debit, reverse=True)
        idx_80 = int(0.8 * 12) # Rank ke-9/10
        if idx_80 >= 12: idx_80 = 11
        q80 = q_sorted[idx_80]
        
        return {
            "Debit_Bulanan": hasil_debit,
            "Q80_Andalan": round(q80, 3)
        }
