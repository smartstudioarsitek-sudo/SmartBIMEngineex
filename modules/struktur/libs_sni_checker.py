import pandas as pd
import numpy as np

# =====================================================================
# MODUL 1: EVALUASI KINERJA SEISMIK (SNI 1726:2019)
# =====================================================================
class GempaSNI1726:
    """
    Modul Evaluasi Kinerja Struktur (Drift & P-Delta) Berdasarkan SNI 1726:2019
    Disiapkan untuk Integrasi SIMBG - SmartBIM Engineex
    """
    def __init__(self, Cd, Ie, kategori_risiko='II'):
        self.Cd = Cd  
        self.Ie = Ie  
        self.kategori_risiko = kategori_risiko
        self.rho_izin = self._get_allowable_drift_ratio()

    def _get_allowable_drift_ratio(self):
        """Menentukan batas izin simpangan (Tabel 20 SNI 1726:2019)"""
        if self.kategori_risiko in ['I', 'II']: return 0.020
        elif self.kategori_risiko == 'III': return 0.015
        elif self.kategori_risiko == 'IV': return 0.010
        else: return 0.020 

    def check_story_drift(self, df_fem_disp):
        """Kalkulasi Simpangan Antar Lantai (Story Drift) SNI 1726 Psl 7.8.6"""
        df = df_fem_disp.copy()
        df['Selisih_Delta_xe'] = df['Delta_xe_mm'].diff().fillna(df['Delta_xe_mm'])
        df['Delta_x_mm'] = (self.Cd * df['Selisih_Delta_xe']) / self.Ie
        df['Delta_a_mm'] = self.rho_izin * df['Tinggi_hsx_mm']
        df['Status_Drift'] = np.where(df['Delta_x_mm'] <= df['Delta_a_mm'], '✅ OK', '❌ NG')
        return df.round({'Selisih_Delta_xe': 2, 'Delta_x_mm': 2, 'Delta_a_mm': 2})

    def check_p_delta(self, df_pdelta_input):
        """Kalkulasi Efek P-Delta (Koefisien Stabilitas Theta) SNI 1726 Psl 7.8.7"""
        df = df_pdelta_input.copy()
        df['Theta'] = (df['Px_kN'] * df['Delta_x_mm'] * self.Ie) / (df['Vx_kN'] * df['Tinggi_hsx_mm'] * self.Cd)
        
        beta = 1.0 
        theta_max_calc = 0.5 / (beta * self.Cd)
        self.theta_max = min(theta_max_calc, 0.25)
        df['Theta_Max'] = self.theta_max
        
        conditions = [
            (df['Theta'] <= 0.10),
            (df['Theta'] > 0.10) & (df['Theta'] <= df['Theta_Max']),
            (df['Theta'] > df['Theta_Max'])
        ]
        choices = [
            '✅ AMAN (Abaikan)', 
            '⚠️ PERLU AMPLIFIKASI', 
            '❌ DESAIN ULANG'
        ]
        df['Status_PDelta'] = np.select(conditions, choices, default='Error')
        return df.round({'Theta': 4, 'Theta_Max': 3, 'Px_kN': 2, 'Vx_kN': 2})


# =====================================================================
# MODUL 2: EVALUASI DESAIN BETON BERTULANG (SNI 2847:2019)
# =====================================================================
class BetonSNI2847:
    """
    Modul Audit Kapasitas Penampang Beton (SCWB & Geser Kapasitas) SNI 2847:2019
    Menerima data geometri dan tulangan dari ekstraksi BIM/OCR.
    """
    def __init__(self, fc_mpa, fy_mpa):
        self.fc = fc_mpa  # Mutu Beton (MPa)
        self.fy = fy_mpa  # Mutu Baja Tulangan (MPa)

    def check_scwb(self, df_joints):
        """
        Kontrol Strong Column - Weak Beam (SNI 2847 Psl 18.7.3.2)
        df_joints harus memiliki: ['Node_ID', 'Sum_Mnc_kNm', 'Sum_Mnb_kNm']
        """
        df = df_joints.copy()
        
        # Hitung rasio Mnc / Mnb
        df['Rasio_SCWB'] = df['Sum_Mnc_kNm'] / df['Sum_Mnb_kNm']
        
        # SNI 2847 mensyaratkan Rasio >= 1.2
        df['Batas_Minimum'] = 1.2
        df['Status_SCWB'] = np.where(df['Rasio_SCWB'] >= 1.2, '✅ MEMENUHI', '❌ KOLOM LEMAH')
        
        return df.round({'Rasio_SCWB': 2})

    def calculate_mpr_and_shear(self, df_beams):
        """
        Kalkulasi Probable Moment (Mpr) dan Geser Desain (Ve) (SNI 2847 Psl 18.6.5)
        df_beams harus memiliki: 
        ['Elemen_ID', 'b_mm', 'd_mm', 'As_tarik_mm2', 'Ln_m', 'Vg_gravitasi_kN']
        """
        df = df_beams.copy()
        
        # 1. Menghitung Gaya Tarik Probable pada baja (As * 1.25 * fy) dalam Newton
        T_pr_N = df['As_tarik_mm2'] * (1.25 * self.fy)
        
        # 2. Menghitung tinggi blok tegangan ekuivalen (a) dalam mm
        # Asumsi tulangan tekan diabaikan untuk konservatif (sesuai standar praktis TPA)
        a_mm = T_pr_N / (0.85 * self.fc * df['b_mm'])
        
        # 3. Menghitung Momen Probable (Mpr) dalam kN.m
        # Rumus: Mpr = T_pr * (d - a/2) / 10^6
        df['Mpr_kNm'] = (T_pr_N * (df['d_mm'] - (a_mm / 2))) / 1_000_000
        
        # 4. Menghitung Geser Desain Kapasitas (Ve)
        # Asumsi Mpr terjadi di kedua ujung balok (Mpr1 = Mpr2) menahan goyangan
        # Ve = Vg_gravitasi + (Mpr1 + Mpr2) / Ln
        df['Geser_Mpr_kN'] = (2 * df['Mpr_kNm']) / df['Ln_m']
        df['Ve_Desain_kN'] = df['Vg_gravitasi_kN'] + df['Geser_Mpr_kN']
        
        # Formatting untuk UI
        return df.round({'Mpr_kNm': 2, 'Geser_Mpr_kN': 2, 'Ve_Desain_kN': 2})

# === CONTOH PENGGUNAAN DI APP STREAMLIT NANTI ===
if __name__ == "__main__":
    print("--- TESTING MODUL BETON SNI 2847 ---")
    beton_checker = BetonSNI2847(fc_mpa=30, fy_mpa=420)
    
    # Dummy Data SCWB
    data_joint = {
        'Node_ID': ['J-101', 'J-102', 'J-103'],
        'Sum_Mnc_kNm': [850, 900, 600], # Total kapasitas kolom
        'Sum_Mnb_kNm': [600, 700, 550]  # Total kapasitas balok
    }
    df_scwb = pd.DataFrame(data_joint)
    print("\n1. Hasil Evaluasi SCWB:")
    print(beton_checker.check_scwb(df_scwb))
    
    # Dummy Data Geser Kapasitas (Mpr)
    data_beam = {
        'Elemen_ID': ['B-1 (Kiri)', 'B-1 (Kanan)'],
        'b_mm': [300, 300],
        'd_mm': [440, 440], # Tinggi efektif (500 - selimut)
        'As_tarik_mm2': [1570, 1570], # Misal 5 D 20
        'Ln_m': [5.5, 5.5], # Bentang bersih
        'Vg_gravitasi_kN': [45.5, 45.5] # Geser akibat beban mati + hidup
    }
    df_mpr = pd.DataFrame(data_beam)
    print("\n2. Hasil Geser Kapasitas (Mpr & Ve):")
    print(beton_checker.calculate_mpr_and_shear(df_mpr))
