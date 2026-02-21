import math
import pandas as pd
import numpy as np

class JIAT_Engine:
    """
    Engine untuk Jaringan Irigasi Air Tanah (JIAT).
    Fokus: Hidrolika Pipa (Hazen-Williams) & Geohidrologi Sumur.
    """
    
    def __init__(self):
        pass

    # =========================================
    # 1. ANALISA SUMUR (GEOHIDROLOGI)
    # =========================================
    def hitung_debit_aman_sumur(self, k_perm_m_hari, tebal_akuifer, drawdown_izin, radius_sumur=0.15, sf_persen=80):
        """
        Menghitung Safe Yield Sumur menggunakan pendekatan Cooper-Jacob / Thiem Sederhana.
        """
        T = k_perm_m_hari * tebal_akuifer
        
        k_detik = k_perm_m_hari / 86400
        R_influence = 3000 * drawdown_izin * math.sqrt(k_detik)
        
        if R_influence <= radius_sumur: 
            R_influence = radius_sumur + 50.0 
            
        try:
            Q_teoritis_m3_hari = (2 * math.pi * T * drawdown_izin) / math.log(R_influence / radius_sumur)
            Q_teoritis_lps = (Q_teoritis_m3_hari * 1000) / 86400
        except:
            Q_teoritis_lps = 0
            
        Q_safe = Q_teoritis_lps * (sf_persen / 100.0)
        
        return {
            "Q_Teoritis_Lps": round(Q_teoritis_lps, 2),
            "Q_Aman_Lps": round(Q_safe, 2),
            "Radius_Pengaruh_m": round(R_influence, 1),
            "Transmisivitas": round(T, 2)
        }

    # =========================================
    # 2. HIDROLIKA PIPA (HAZEN-WILLIAMS)
    # =========================================
    def hitung_head_loss_pipa(self, panjang_m, diameter_mm, debit_lps, c_hazen=140):
        """
        Menghitung Mayor Loss menggunakan Hazen-Williams.
        """
        d_meter = diameter_mm / 1000.0
        q_m3s = debit_lps / 1000.0
        
        if q_m3s <= 0 or d_meter <= 0: return 0, 0
        
        area = 0.25 * math.pi * (d_meter**2)
        v = q_m3s / area
        
        hf = 10.67 * panjang_m * (q_m3s ** 1.852) / ((c_hazen ** 1.852) * (d_meter ** 4.87))
        
        return round(hf, 3), round(v, 2)

    def rekomendasi_pompa(self, Q_desain_lps, Head_Statis, Total_Panjang_Pipa, Diameter_Avg_mm):
        """
        Estimasi Head Total Pompa & Daya.
        """
        hf, v = self.hitung_head_loss_pipa(Total_Panjang_Pipa, Diameter_Avg_mm, Q_desain_lps)
        hf_total = hf * 1.1 
        
        Head_Manometrik = Head_Statis + hf_total
        
        rho = 1000 # kg/m3
        g = 9.81
        Q_m3s = Q_desain_lps / 1000
        eff_pompa = 0.70
        
        Power_kW = (rho * g * Q_m3s * Head_Manometrik) / (1000 * eff_pompa)
        
        return {
            "Q_Desain_Lps": Q_desain_lps,
            "Head_Total_m": round(Head_Manometrik, 2),
            "Power_kW": round(Power_kW, 2),
            "Power_HP": round(Power_kW * 1.341, 2)
        }

    # =========================================
    # 3. GENERATOR KURVA POMPA (MODUL TPA)
    # =========================================
    def generate_pump_system_curve(self, Q_target_lps, H_statis, L_pipa, D_pipa_mm, C_hw=130):
        """
        [MODUL AUDIT TPA] Menghasilkan data untuk plotting Kurva Head-Discharge Pompa JIAT.
        Mengkalibrasi perpotongan antara System Curve dan Pump Performance Curve.
        """
        q_vals = np.linspace(0, Q_target_lps * 1.5, 50)
        
        h_sys = []
        h_pump = []
        
        H_shutoff = H_statis * 1.5 
        
        hf_target, _ = self.hitung_head_loss_pipa(L_pipa, D_pipa_mm, Q_target_lps, C_hw)
        H_target_sys = H_statis + (hf_target * 1.1) 
        
        K_pump = (H_shutoff - (H_target_sys * 1.05)) / (Q_target_lps**2)
        
        for q in q_vals:
            if q == 0:
                hf = 0
            else:
                hf, _ = self.hitung_head_loss_pipa(L_pipa, D_pipa_mm, q, C_hw)
            
            hs = H_statis + (hf * 1.1)
            h_sys.append(hs)
            
            hp = H_shutoff - K_pump * (q**2)
            h_pump.append(max(0, hp)) 
            
        df_curve = pd.DataFrame({
            "Debit (L/s)": q_vals,
            "System Head (m)": h_sys,
            "Pump Head (m)": h_pump
        })
        
        return df_curve, H_target_sys
