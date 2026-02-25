import math
import pandas as pd
import numpy as np

class SNIBeton2019:
    """
    LIBRARY ANALISIS STRUKTUR BETON BERTULANG
    Referensi: SNI 2847:2019 (Persyaratan Beton Struktural untuk Bangunan Gedung)
    Created for: SmartBIMEngineex Forensic Audit
    """

    @staticmethod
    def get_beta1(fc):
        """
        Menghitung faktor beta1 untuk distribusi tegangan beton (Pasal 22.2.2.4.3)
        fc dalam MPa
        """
        if fc <= 28:
            return 0.85
        else:
            beta = 0.85 - 0.05 * ((fc - 28) / 7)
            return max(beta, 0.65)

    @staticmethod
    def analyze_column_capacity(b, h, fc, fy, total_rebar_area, Pu_input, Mu_input=0):
        """
        AUDIT FORENSIK KOLOM (P-M INTERACTION CHECK)
        ---------------------------------------------
        Input:
        b, h : Dimensi kolom (mm)
        fc   : Mutu beton (MPa)
        fy   : Mutu baja (MPa)
        total_rebar_area : Luas tulangan total Ast (mm2)
        Pu_input : Beban Aksial Terfaktor (kN)
        Mu_input : Momen Terfaktor (kNm)
        
        Output: Dictionary lengkap status keamanan & DCR
        """
        # 1. Properti Penampang
        Ag = b * h # Luas kotor
        Ast = total_rebar_area
        
        # 2. Kapasitas Aksial Murni (Pn0) - Pasal 22.4.2.2
        # Pn0 = 0.85*fc*(Ag-Ast) + fy*Ast
        Pn0 = 0.85 * fc * (Ag - Ast) + fy * Ast # Newton
        
        # 3. Kapasitas Aksial Maksimum (Pn_max) - Pasal 22.4.2.1
        # Faktor 0.80 untuk sengkang ikat (Tied Column)
        Pn_max = 0.80 * Pn0 
        
        # 4. Faktor Reduksi Kekuatan (Phi) - Pasal 21.2
        # Asumsi kolom terkekang sengkang biasa (bukan spiral) -> phi = 0.65 (Compression Controlled)
        phi = 0.65 
        
        # 5. Kapasitas Desain (Phi Pn)
        Phi_Pn_max = phi * Pn_max
        
        # Konversi ke kN untuk pelaporan
        Cap_Aksial_kN = Phi_Pn_max / 1000
        
        # 6. HITUNG DCR (Demand Capacity Ratio)
        # DCR = Beban / Kapasitas
        dcr_aksial = Pu_input / Cap_Aksial_kN
        
        # 7. Status Keamanan
        status = "AMAN (SAFE)" if dcr_aksial <= 1.0 else "BAHAYA (UNSAFE)"
        
        return {
            "Komponen": f"Kolom {b}x{h}",
            "Kapasitas_Max (kN)": round(Cap_Aksial_kN, 2),
            "Beban_Rencana (kN)": round(Pu_input, 2),
            "DCR_Ratio": round(dcr_aksial, 3),
            "Status": status,
            "Phi_Used": phi,
            "Ref_SNI": "SNI 2847:2019 Pasal 22.4"
        }

    @staticmethod
    def generate_interaction_diagram(b, h, fc, fy, ast, cover=40):
        """
        [AUDIT PATCH]: GENERATOR KURVA INTERAKSI P-M BERBASIS FISIKA MURNI
        Menghitung kapasitas kolom menggunakan prinsip kompatibilitas regangan.
        """
        beta1 = SNIBeton2019.get_beta1(fc)
        Ag = b * h
        As_tot = ast
        d = h - cover
        d_prime = cover
        
        # Strain compatibility parameters
        ecu = 0.003
        Es = 200000.0
        ey = fy / Es
        
        M_points = []
        P_points = []
        
        # Iterasi dari c = besar (tekan murni) ke c = kecil (tarik murni)
        c_vals = np.linspace(h * 1.5, 1.0, 50) 
        
        for c in c_vals:
            a = min(beta1 * c, h)
            
            # Regangan baja tulangan (asumsi tulangan simetris 2 sisi)
            es_tarik = ecu * (d - c) / c
            es_tekan = ecu * (c - d_prime) / c
            
            # Tegangan baja (dibatasi oleh fy)
            fs_tarik = min(max(es_tarik * Es, -fy), fy)
            fs_tekan = min(max(es_tekan * Es, -fy), fy)
            
            # Gaya dalam
            Cc = 0.85 * fc * a * b
            Cs = (fs_tekan - 0.85 * fc) * (As_tot / 2) # Koreksi beton yang terdesak baja
            Ts = fs_tarik * (As_tot / 2)
            
            # Kapasitas Nominal
            Pn = Cc + Cs - Ts
            Mn = Cc * (h/2 - a/2) + Cs * (h/2 - d_prime) + Ts * (d - h/2)
            
            # Faktor reduksi (phi) - Transisi dari Tekan ke Tarik
            if es_tarik <= ey: phi = 0.65
            elif es_tarik >= 0.005: phi = 0.90
            else: phi = 0.65 + (es_tarik - ey) * (0.25 / (0.005 - ey))
            
            # Batasan Pn max (0.80 Pn0 untuk sengkang ikat)
            Pn0 = 0.85 * fc * (Ag - As_tot) + fy * As_tot
            Pn_max = 0.80 * Pn0
            
            Pn_design = min(phi * Pn, phi * Pn_max)
            Mn_design = phi * Mn
            
            if Pn_design >= 0: # Hanya ambil area tekan dan lentur positif
                P_points.append(Pn_design / 1000) # ke kN
                M_points.append(Mn_design / 1000000) # ke kNm
                
        # Tambahkan titik 0,0 untuk menutup area grafik
        M_points.append(0)
        P_points.append(0)

        # Cari titik kunci untuk laporan
        Point_A = (0, max(P_points))
        Point_C = (max(M_points), 0)
        Point_B = (max(M_points), np.interp(max(M_points), M_points[::-1], P_points[::-1]))

        return {
            "Point_A (Tekan)": Point_A,
            "Point_B (Balance)": Point_B,
            "Point_C (Lentur)": Point_C,
            "Plot_Data": pd.DataFrame({
                "M_Capacity": M_points,
                "P_Capacity": P_points
            })
        }
    
    @staticmethod
    def analyze_beam_flexure(b, h, fc, fy, As_bottom, Mu_input, cover=40):
        """
        AUDIT FORENSIK BALOK (Momen Lentur)
        -----------------------------------
        As_bottom: Luas tulangan tarik (mm2)
        Mu_input: Momen Perlu (kNm)
        """
        d = h - cover
        
        # 1. Hitung tinggi blok tekan beton (a) - Pasal 22.2.2.4.1
        # a = (As * fy) / (0.85 * fc * b)
        a = (As_bottom * fy) / (0.85 * fc * b)
        
        # 2. Cek apakah a < h (Validasi Geometri)
        if a > h:
            return {"Status": "GAGAL (Concrete Crushing)", "DCR": 9.99}
            
        # 3. Hitung Momen Nominal (Mn)
        Mn = As_bottom * fy * (d - a/2) # N.mm
        
        # 4. Faktor Reduksi (Phi) - Lentur Murni
        phi = 0.90
        
        # 5. Kapasitas Desain
        Phi_Mn = phi * Mn
        Cap_Momen_kNm = Phi_Mn / 1000000
        
        # 6. DCR Check
        dcr = Mu_input / Cap_Momen_kNm
        status = "AMAN (SAFE)" if dcr <= 1.0 else "KRITIS (UNSAFE)"
        
        return {
            "Komponen": f"Balok {b}x{h}",
            "Tulangan_Tarik": f"{As_bottom} mm2",
            "Kapasitas_Momen (kNm)": round(Cap_Momen_kNm, 2),
            "Momen_Rencana (kNm)": round(Mu_input, 2),
            "DCR_Ratio": round(dcr, 3),
            "Status": status,
            "Ref_SNI": "SNI 2847:2019 Pasal 21.2"
        }
