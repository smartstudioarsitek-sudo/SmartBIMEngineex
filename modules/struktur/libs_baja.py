import math

class SNI_Steel_2020:
    def __init__(self, fy, E=200000):
        self.fy = float(fy)
        self.E = float(E) # Modulus Elastisitas Baja (MPa)

    def hitung_kekakuan_dam(self, I_profil, A_profil, P_required, P_yield):
        """
        Menghitung Kekakuan Tereduksi (EI* dan EA*) sesuai Direct Analysis Method (DAM).
        SNI 1729:2020 Pasal C2.3.
        Reviewer Note: Menerapkan reduksi kekakuan 0.8 * Tau_b.
        """
        # 1. Hitung Rasio Beban (Pr / Py)
        # Pr = Kekuatan Perlu (P_required)
        # Py = Kekuatan Leleh Aksial (Ag * fy)
        
        if P_yield == 0: alpha = 0
        else: alpha = P_required / P_yield
        
        # 2. Hitung Tau_b (Faktor Reduksi Kekakuan Inelastis) - Pasal C2.3(b)
        # Jika alpha <= 0.5 -> Tau_b = 1.0
        # Jika alpha > 0.5 -> Tau_b = 4 * alpha * (1 - alpha)
        
        if alpha <= 0.5:
            tau_b = 1.0
            ket = "Elastis (Alpha <= 0.5)"
        else:
            tau_b = 4 * alpha * (1 - alpha)
            ket = "Inelastis (Alpha > 0.5)"
            
        # 3. Hitung Kekakuan Tereduksi
        # EI* = 0.8 * Tau_b * EI
        # EA* = 0.8 * EA
        
        EI_reduced = 0.8 * tau_b * self.E * I_profil
        EA_reduced = 0.8 * self.E * A_profil
        
        trace_msg = (f"Rasio Pr/Py = {alpha:.3f} ({ket}) -> Tau_b = {tau_b:.3f}. "
                     f"Kekakuan Lentur Direduksi (EI*) = 0.8 * {tau_b:.3f} * EI")
                     
        return EI_reduced, EA_reduced, tau_b, trace_msg

    def cek_tekuk_lokal(self, b, t, limit_r):
        """Cek kelangsingan pelat (Compact/Non-Compact)"""
        lamda = b / t
        status = "Compact" if lamda <= limit_r else "Non-Compact/Slender"
        return status, lamda
# [PATCH UPGRADE] libs_baja.py

def check_steel_column(Pu, Ag, fy, profil_name):
    """
    Forensik Kapasitas Kolom Baja (Simplified AISC/SNI)
    Pu: Beban Terfaktor (Ton)
    Ag: Luas Penampang (cm2)
    fy: Mutu Baja (Mpa)
    """
    # Konversi unit
    Pn_nominal = 0.9 * fy * (Ag * 100) # Newton (0.9 fy Ag - Simplified Yielding)
    Pn_ton = Pn_nominal / 10000 # Ke Ton
    
    # Faktor Reduksi SNI (Tekan)
    phi = 0.90 
    phi_Pn = phi * Pn_ton
    
    # Hitung DCR
    dcr = Pu / phi_Pn
    
    status = "AMAN (SAFE)" if dcr < 1.0 else "BAHAYA (UNSAFE)"
    
    return {
        "Profil": profil_name,
        "Demand (Pu)": round(Pu, 2),
        "Capacity (phi Pn)": round(phi_Pn, 2),
        "DCR Ratio": round(dcr, 3),
        "Status": status
    }
