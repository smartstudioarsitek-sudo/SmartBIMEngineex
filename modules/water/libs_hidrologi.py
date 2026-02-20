import numpy as np
import pandas as pd
import math
from scipy.stats import pearson3 # Wajib untuk Log Pearson Tipe III yang presisi

class Hidrologi_Engine:
    """
    Engine Terpadu untuk Analisis Hidrologi (SNI 2415:2016 & KP-01):
    1. Klimatologi (Penman Modifikasi)
    2. Curah Hujan Rancangan (Gumbel & Log Pearson III)
    3. Hujan Efektif (NRCS Curve Number)
    4. Hidrograf Satuan Sintetis (HSS Nakayasu)
    5. Ketersediaan Air (FJ Mock)
    """
    
    def __init__(self):
        pass

    # =======================================================
    # 1. ANALISIS FREKUENSI HUJAN (GUMBEL & LOG PEARSON III)
    # =======================================================
    def analisis_frekuensi_hujan(self, data_hujan_max):
        """
        Input: List data hujan harian maksimum tahunan.
        Output: Curah hujan rencana (R2, R5, R10, R25, R50, R100)
        Memenuhi syarat komparasi SNI 2415:2016.
        """
        arr = np.array(data_hujan_max)
        n = len(arr)
        
        if n < 2:
            return {"Error": "Data kurang, minimal 2 tahun data."}
        
        # --- A. Statistik Dasar ---
        mu = np.mean(arr)
        std = np.std(arr, ddof=1)
        Cs = pd.Series(arr).skew()
        
        # --- B. Metode Gumbel (Tipe I Extrem) ---
        yn = 0.4952 + (0.0006 * n) # Aproksimasi Reduced Mean
        sn = 0.9496 + (0.0025 * n) # Aproksimasi Reduced Std
        periods = [2, 5, 10, 25, 50, 100]
        hasil_gumbel = {}
        
        for T in periods:
            prob = 1 - (1/T)
            yt = -math.log(-math.log(prob))
            K_gumbel = (yt - yn) / sn
            Xt = mu + (K_gumbel * std)
            hasil_gumbel[f"R{T}"] = round(Xt, 1)

        # --- C. Metode Log Pearson Tipe III (Standar Utama PUPR) ---
        # Transformasi logaritmik basis 10
        log_arr = np.log10(arr)
        log_mu = np.mean(log_arr)
        log_std = np.std(log_arr, ddof=1)
        log_skew = pd.Series(log_arr).skew()
        
        hasil_lp3 = {}
        for T in periods:
            # SciPy pearson3.ppf membutuhkan input kumulatif probabilitas (1 - 1/T)
            prob_cum = 1 - (1/T)
            # Menghitung nilai Log X berdasarkan faktor frekuensi K
            log_X = pearson3.ppf(prob_cum, skew=log_skew, loc=log_mu, scale=log_std)
            # Kembalikan ke nilai asli (Anti-Log)
            hasil_lp3[f"R{T}"] = round(10**log_X, 1)
            
        return {
            "Statistik_Dasar": {"Mean": round(mu, 2), "Std_Dev": round(std, 2), "Skewness": round(Cs, 3)},
            "Statistik_Log": {"Log_Mean": round(log_mu, 3), "Log_Std": round(log_std, 3), "Log_Skew": round(log_skew, 3)},
            "Curah_Hujan_Gumbel_mm": hasil_gumbel,
            "Curah_Hujan_LP3_mm": hasil_lp3
        }

    # =======================================================
    # 2. HUJAN EFEKTIF (NRCS - CURVE NUMBER)
    # =======================================================
    def hitung_hujan_efektif_cn(self, P_total_mm, CN):
        """
        Menghitung Hujan Efektif (Pe) menggunakan metode SCS/NRCS Curve Number.
        Memperhitungkan infiltrasi berdasarkan tutupan lahan (Land Use).
        """
        if CN <= 0 or CN >= 100: return 0.0
        
        # Potensi Retensi Maksimum (S) dalam mm
        S_mm = (25400 / CN) - 254
        
        # Initial Abstraction (Ia) - Kehilangan awal sebelum limpasan
        Ia = 0.2 * S_mm
        
        # Jika hujan total lebih kecil dari serapan awal, tidak ada limpasan
        if P_total_mm <= Ia:
            return 0.0
            
        # Hujan Efektif / Limpasan Langsung (Pe)
        Pe = ((P_total_mm - Ia)**2) / (P_total_mm - Ia + S_mm)
        
        return round(Pe, 2)

    # =======================================================
    # 3. HIDROGRAF SATUAN SINTETIS (HSS) NAKAYASU
    # =======================================================
    def hitung_hss_nakayasu(self, A_km2, L_km, R0_mm=1.0, alpha=2.0, dt=1.0):
        """
        Menghasilkan Kurva Hidrograf Banjir Nakayasu (Waktu vs Debit).
        R0_mm: Hujan efektif (Biasanya diset 1mm untuk Unit Hidrograf, 
               atau diisi nilai Pe riil untuk Hidrograf Banjir)
        alpha: Parameter karakteristik DAS (1.5 - 3.0, default 2.0)
        """
        # 1. Waktu Kelambatan (Time Lag - Tg)
        if L_km > 15:
            Tg = 0.4 + 0.058 * L_km
        else:
            Tg = 0.21 * (L_km ** 0.7)
            
        # 2. Durasi Hujan (Tr) & Waktu Puncak (Tp)
        Tr = 0.75 * Tg  # Rule of thumb: 0.5 Tg s/d 1.0 Tg
        Tp = Tg + 0.8 * Tr
        
        # 3. Waktu penurunan hingga 30% debit puncak (T0.3)
        T03 = alpha * Tg
        
        # 4. Debit Puncak (Qp)
        # Rumus: Qp = (C * A * R0) / (3.6 * (0.3*Tp + T0.3))
        # Karena R0 dalam mm, A dalam km2, faktor konversi 3.6 menghasilkan m3/s
        Qp = (A_km2 * R0_mm) / (3.6 * (0.3 * Tp + T03))
        
        # 5. Konstruksi Kurva (Lengkung Naik & Turun)
        time_arr = np.arange(0, Tp + 4*T03, dt) # Rentang waktu simulasi
        Q_arr = []
        
        for t in time_arr:
            if t <= Tp:
                # Kurva Naik (Rising Limb)
                Qt = Qp * ((t / Tp) ** 2.4)
            elif t <= Tp + T03:
                # Kurva Turun Bagian 1 (> 30% Qp)
                Qt = Qp * (0.3 ** ((t - Tp) / T03))
            elif t <= Tp + T03 + 1.5 * T03:
                # Kurva Turun Bagian 2 (30% - 9% Qp)
                Qt = Qp * (0.3 ** ((t - Tp + 0.5 * T03) / (1.5 * T03)))
            else:
                # Kurva Turun Bagian 3 (< 9% Qp)
                Qt = Qp * (0.3 ** ((t - Tp + 1.5 * T03) / (2.0 * T03)))
                
            Q_arr.append(round(Qt, 3))
            
        df_hidrograf = pd.DataFrame({
            "Waktu (Jam)": time_arr,
            "Debit (m3/s)": Q_arr
        })
        
        parameter_kunci = {
            "Time Lag (Tg)": f"{Tg:.2f} jam",
            "Time Peak (Tp)": f"{Tp:.2f} jam",
            "Debit Puncak (Qp)": f"{Qp:.2f} m3/s",
            "Alpha (Karakter DAS)": alpha
        }
        
        return df_hidrograf, parameter_kunci

    # =======================================================
    # 4. KLIMATOLOGI PENMAN & FJ MOCK (KODE LAMA DIAMANKAN)
    # =======================================================
    def hitung_eto_penman(self, t_mean, rh_mean, sun_pct, u_ms, letak_lintang, elevasi, bulan_idx):
        ea = 6.11 * math.exp((17.27 * t_mean) / (t_mean + 237.3))
        ed = ea * (rh_mean / 100)
        fu = 0.27 * (1 + 0.864 * u_ms)
        ra_table = [15.1, 15.4, 15.2, 14.5, 13.6, 13.1, 13.4, 14.2, 15.0, 15.4, 15.3, 15.0]
        Ra = ra_table[bulan_idx % 12]
        Rs = (0.25 + 0.54 * (sun_pct / 100)) * Ra
        Rns = 0.75 * Rs
        ft = 2.043e-10 * ((t_mean + 273.16)**4)
        fed = 0.34 - 0.044 * math.sqrt(ed)
        fsun = 0.1 + 0.9 * (sun_pct / 100)
        Rnl = ft * fed * fsun
        Rn = Rns - Rnl
        delta = 4098 * (0.6108 * math.exp(17.27 * t_mean / (t_mean + 237.3))) / ((t_mean + 237.3)**2)
        P = 101.3 * ((293 - 0.0065 * elevasi) / 293)**5.26
        gamma = 0.665e-3 * P * 10 
        W = delta / (delta + gamma)
        c = 0.90 
        ETo = c * (W * Rn + (1 - W) * fu * (ea - ed))
        return max(0.0, round(ETo, 2))

    def simulasi_fj_mock(self, hujan_bulanan_mm, eto_bulanan_mm_hari, luas_das_km2):
        hasil_debit = []
        V_storage, SMC_max = 100.0, 200.0 
        Infiltration_Coeff, Recession_Factor = 0.4, 0.6 
        
        for i in range(12):
            R = hujan_bulanan_mm[i]
            Et_pot = eto_bulanan_mm_hari[i] * 30.0 
            Et_act = Et_pot if R > Et_pot else R + (Et_pot - R) * 0.5
            WS = R - Et_act 
            V_new = max(0, min(V_storage + WS, SMC_max))
            dV = V_new - V_storage 
            V_storage = V_new 
            WS_net = max(0, WS - dV)
            Baseflow = WS_net * Infiltration_Coeff
            DirectRunoff = WS_net - Baseflow
            Total_RO_mm = Baseflow + DirectRunoff + (V_storage * 0.05 * Recession_Factor)
            Q_m3s = (Total_RO_mm * 1000 * luas_das_km2) / (30 * 86400)
            hasil_debit.append(max(0, Q_m3s))
            
        q_sorted = sorted(hasil_debit, reverse=True)
        idx_80 = min(int(0.8 * 12), 11)
        return {"Debit_Bulanan": hasil_debit, "Q80_Andalan": round(q_sorted[idx_80], 3)}

# === TESTING BLOK ===
if __name__ == "__main__":
    hydro = Hidrologi_Engine()
    
    # 1. Test Log Pearson III
    data_hujan = [85.5, 92.1, 105.4, 78.2, 115.0, 99.5, 88.0, 140.2, 110.5, 95.0]
    hasil_stat = hydro.analisis_frekuensi_hujan(data_hujan)
    print("Curah Hujan Rencana (Log Pearson III):", hasil_stat['Curah_Hujan_LP3_mm'])
    
    # 2. Test Curve Number
    pe = hydro.hitung_hujan_efektif_cn(P_total_mm=hasil_stat['Curah_Hujan_LP3_mm']['R50'], CN=75)
    print(f"Hujan Efektif (Pe) untuk CN 75: {pe} mm")
    
    # 3. Test HSS Nakayasu
    df_hss, params = hydro.hitung_hss_nakayasu(A_km2=25.5, L_km=8.5, R0_mm=pe)
    print("Parameter Nakayasu:", params)
    print(df_hss.head())
