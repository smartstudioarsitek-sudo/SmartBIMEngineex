import numpy as np
import math

class Irrigation_Engine:
    
    def hitung_dimensi_saluran(self, Q, b_ratio=1.5, m=1.0, S=0.0005, n=0.025):
        """
        Desain Dimensi Saluran Trapesium Otomatis.
        b_ratio = b/h (rasio lebar terhadap tinggi)
        """
        # Iterasi mencari h
        h = 0.1
        found = False
        for _ in range(100):
            b = h * b_ratio
            A = (b + m * h) * h
            P = b + 2 * h * math.sqrt(1 + m**2)
            R = A / P
            
            # Manning
            Q_calc = (1/n) * A * (R**(2/3)) * (S**0.5)
            
            if Q_calc >= Q:
                found = True
                break
            h += 0.05
            
        if not found: return None
        
        # Cek Froude & Kecepatan
        V = Q / A
        T = b + 2 * m * h
        D = A / T
        Fr = V / math.sqrt(9.81 * D)
        
        status = "AMAN"
        if Fr >= 1.0: status = "SUPERKRITIS (Bahaya Gerusan)"
        if V < 0.6: status += " (Bahaya Endapan)"
        
        # Tinggi Jagaan (KP-03)
        w = 0.2 + (0.04 * (Q**(1/3))) # Rumus empiris simple
        H_total = h + w
        
        return {
            "Dimensi": {"b": round(b, 2), "h_air": round(h, 2), "H_total": round(H_total, 2), "m": m},
            "Hidrolis": {"V": round(V, 2), "Fr": round(Fr, 2), "Q_cap": round(Q_calc, 2)},
            "Status": status
        }

    def generate_dxf_script(self, desain_data):
        """Generates simple DXF content (text format) for the channel."""
        b = desain_data['Dimensi']['b']
        H = desain_data['Dimensi']['H_total']
        m = desain_data['Dimensi']['m']
        
        # Koordinat Trapesium (0,0 di as dasar)
        x_bl = -b/2; y_b = 0
        x_br = b/2
        x_tl = -b/2 - (m*H); y_t = H
        x_tr = b/2 + (m*H)
        
        dxf = "0\nSECTION\n2\nENTITIES\n"
        
        # Fungsi Line Helper
        def add_line(x1, y1, x2, y2, layer):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
            
        dxf += add_line(x_tl, y_t, x_bl, y_b, "TANAH")
        dxf += add_line(x_bl, y_b, x_br, y_b, "DASAR")
        dxf += add_line(x_br, y_b, x_tr, y_t, "TANAH")
        
        dxf += "0\nENDSEC\n0\nEOF"
        return dxf

    def hitung_parshall_flume(self, Q_input, lebar_leher_m=None):
        """
        Menghitung dimensi Parshall Flume atau Debit dari tinggi muka air.
        Jika lebar_leher_m diisi, hitung H. Jika tidak, rekomendasikan lebar.
        """
        # Tabel Konstanta Parshall (Simple version)
        # W(ft) -> C, n
        # Konversi W meter ke ft: W_ft = W_m / 0.3048
        
        # Rekomendasi W berdasarkan Q (KP-01/USBR)
        if lebar_leher_m is None:
            if Q_input < 0.03: W = 0.076 # 3 inch
            elif Q_input < 0.18: W = 0.152 # 6 inch
            elif Q_input < 0.40: W = 0.305 # 1 ft
            elif Q_input < 1.10: W = 0.610 # 2 ft
            else: W = 1.0
        else:
            W = lebar_leher_m
            
        # Rumus Q = C * H^n (Metric Unit Approx: Q = K * H^u)
        # Simplified Metric formula: Q = 2.3 * W * H^1.6 (Agak kasar tapi cukup untuk estimasi)
        # H = (Q / (2.3 * W)) ^ (1/1.6)
        
        H_needed = (Q_input / (2.3 * W)) ** (1/1.6)
        
        return {
            "Tipe": f"Parshall Flume W={W*100:.0f} cm",
            "Lebar_Leher": W,
            "H_MukaAir_Hulu": round(H_needed, 3),
            "Q_Max": round(2.3 * W * (0.8**1.6), 2) # Asumsi H max 0.8m
        }
