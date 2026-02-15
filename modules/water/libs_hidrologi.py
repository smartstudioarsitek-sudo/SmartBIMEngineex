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
    4. Kebutuhan Air Irigasi (NFR)
    """
    
    # --- 1. KLIMATOLOGI (PENMAN) ---
    def hitung_eto_penman(self, t_mean, rh_mean, sun_pct, u_ms, letak_lintang, elevasi, bulan_idx):
        """Hitung ETo Harian (mm/hari) metode Penman Modifikasi."""
        # Konstanta & Parameter Fisik
        ea = 6.11 * math.exp((17.27 * t_mean) / (t_mean + 237.3))
        ed = ea * (rh_mean / 100)
        fu = 0.27 * (1 + 0.864 * u_ms)
        
        # Radiasi (Ra) - Simplified Table Lookup approximation for Indonesia (Lat -5 to -8)
        # Ra rata-rata harian (mm/hari) per bulan
        ra_table = [15.1, 15.4, 15.2, 14.5, 13.6, 13.1, 13.4, 14.2, 15.0, 15.4, 15.3, 15.0] 
        Ra = ra_table[bulan_idx % 12]
        
        Rs = (0.25 + 0.54 * (sun_pct / 100)) * Ra
        Rns = 0.75 * Rs
        
        # Longwave
        ft = 2.043e-10 * ((t_mean + 273.16)**4)
        fed = 0.34 - 0.044 * math.sqrt(ed)
        fsun = 0.1 + 0.9 * (sun_pct / 100)
        Rnl = ft * fed * fsun
        Rn = Rns - Rnl
        
        # Weighting Factor W
        delta = 4098 * (0.6108 * math.exp(17.27 * t_mean / (t_mean + 237.3))) / ((t_mean + 237.3)**2)
        P = 101.3 * ((293 - 0.0065 * elevasi) / 293)**5.26
        gamma = 0.665e-3 * P * 10
        W = delta / (delta + gamma)
        
        c = 0.9 # Faktor koreksi Indonesia (KP-01)
        ETo = c * (W * Rn + (1 - W) * fu * (ea - ed))
        return max(0, ETo)

    # --- 2. STATISTIK BANJIR ---
    def analisis_frekuensi_hujan(self, data_hujan_max):
        """Input: List/Array Hujan Harian Maksimum Tahunan."""
        arr = np.array(data_hujan_max)
        if len(arr) < 2: return {"Error": "Data kurang"}
        
        mu = np.mean(arr)
        std = np.std(arr, ddof=1)
        Cs = pd.Series(arr).skew()
        Ck = pd.Series(arr).kurt() + 3
        
        # Gumbel Calculation
        periods = [2, 5, 10, 25, 50, 100]
        hasil_gumbel = {}
        for T in periods:
            prob = 1 - (1/T)
            # Loc & Scale approximation
            sn = 0.9496 # Approx for n=10-100 (Simplified)
            yn = 0.4952
            val = mu + (std/sn) * (-math.log(-math.log(prob)) - yn) # Rumus umum Gumbel
            hasil_gumbel[f"R{T}"] = val
            
        return {
            "Statistik": {"Mean": mu, "Std": std, "Cs": Cs, "Ck": Ck},
            "Hujan_Rencana": hasil_gumbel
        }

    # --- 3. KETERSEDIAAN AIR (MOCK) ---
    def simulasi_fj_mock(self, hujan_bulanan, eto_bulanan, luas_das_km2):
        """Simulasi Debit Andalan Bulanan (Simplified Mock)."""
        hasil = []
        V_storage = 100 # Initial Soil Storage
        for i in range(12):
            R = hujan_bulanan[i]
            E = eto_bulanan[i] * 30
            WS = R - E # Water Surplus
            
            # Storage change
            V_new = V_storage + WS
            if V_new < 0: V_new = 0
            if V_new > 200: V_new = 200 # Soil Cap
            dV = V_new - V_storage
            V_storage = V_new
            
            WS_net = max(0, WS - dV)
            
            # Infiltration & Baseflow
            i_factor = 0.4
            Baseflow = WS_net * i_factor
            DirectRunoff = WS_net - Baseflow
            
            Total_RO_mm = Baseflow + DirectRunoff
            # Konversi ke m3/s
            Q = (Total_RO_mm * 1e-3 * luas_das_km2 * 1e6) / (30 * 86400)
            hasil.append(Q)
            
        # Hitung Q80 (Andalan)
        q_sorted = sorted(hasil)
        idx_80 = int(0.2 * 12)
        q80 = q_sorted[idx_80]
        
        return {"Debit_Bulanan": hasil, "Q80_Andalan": q80}
