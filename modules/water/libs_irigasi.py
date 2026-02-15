import numpy as np
import math

class Irrigation_Engine:
    
    def __init__(self):
        pass

    # =========================================
    # 1. DESAIN SALURAN (MANNING & TRAPESIUM)
    # =========================================
    def hitung_dimensi_saluran(self, Q, b_ratio=1.5, m=1.0, S=0.0005, n=0.025):
        """
        Mencari dimensi saluran trapesium yang ekonomis secara iteratif.
        """
        # Iterasi mencari tinggi air (h)
        h = 0.1
        found = False
        max_h = 10.0 # Safety break
        
        while h < max_h:
            b = h * b_ratio # Lebar dasar proporsional terhadap tinggi
            
            # Properti Geometris
            A = (b + m * h) * h
            P = b + 2 * h * math.sqrt(1 + m**2)
            R = A / P
            
            # Rumus Manning
            Q_calc = (1/n) * A * (R**(2/3)) * (S**0.5)
            
            if Q_calc >= Q:
                found = True
                break
            h += 0.05
            
        if not found:
            return None
        
        # Validasi Hidrolis
        V = Q / A
        T = b + 2 * m * h # Lebar muka air
        D = A / T # Kedalaman hidrolis
        Fr = V / math.sqrt(9.81 * D)
        
        status = "AMAN"
        warns = []
        if Fr >= 1.0: 
            status = "BAHAYA"
            warns.append("Aliran Superkritis (Gerusan)")
        if V < 0.6: 
            status = "PERHATIAN"
            warns.append("Kecepatan < 0.6 m/s (Endapan)")
        if V > 2.0:
            status = "BAHAYA"
            warns.append("Kecepatan > 2.0 m/s (Erosi)")
            
        # Tinggi Jagaan (Freeboard) KP-03
        if Q < 0.5: w = 0.20
        elif Q < 1.5: w = 0.20
        elif Q < 5.0: w = 0.25
        elif Q < 10.0: w = 0.30
        else: w = 0.50
        
        H_total = h + w
        
        return {
            "Dimensi": {
                "b": round(b, 2),
                "h_air": round(h, 2),
                "H_total": round(H_total, 2),
                "m": m,
                "w": w
            },
            "Hidrolis": {
                "V": round(V, 2),
                "Fr": round(Fr, 2),
                "Q_cap": round(Q_calc, 3),
                "Area": round(A, 2)
            },
            "Status": status,
            "Catatan": ", ".join(warns) if warns else "Hidrolis OK"
        }

    # =========================================
    # 2. GENERATOR GAMBAR CAD (.DXF)
    # =========================================
    def generate_dxf_script(self, desain_data):
        """
        Membuat string konten file .DXF sederhana (Text Based) untuk Cross Section.
        Tidak membutuhkan library ezdxf (Manual String Construction).
        """
        b = desain_data['Dimensi']['b']
        H = desain_data['Dimensi']['H_total']
        h_air = desain_data['Dimensi']['h_air']
        m = desain_data['Dimensi']['m']
        
        # Koordinat Trapesium (0,0 di as dasar saluran)
        x_bl = -b/2
        y_b = 0
        x_br = b/2
        
        x_tl = -b/2 - (m*H)
        y_t = H
        x_tr = b/2 + (m*H)
        
        # Koordinat Muka Air
        x_wl = -b/2 - (m*h_air)
        y_w = h_air
        x_wr = b/2 + (m*h_air)
        
        # Header DXF Standard
        dxf = "0\nSECTION\n2\nENTITIES\n"
        
        # Fungsi Helper bikin Garis
        def dxf_line(x1, y1, x2, y2, layer):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
        
        # Fungsi Helper bikin Teks
        def dxf_text(x, y, text, height, layer):
            return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{height}\n1\n{text}\n"

        # 1. Gambar Tanah/Saluran (Layer: STRUKTUR)
        dxf += dxf_line(x_tl, y_t, x_bl, y_b, "STRUKTUR") # Kiri
        dxf += dxf_line(x_bl, y_b, x_br, y_b, "STRUKTUR") # Dasar
        dxf += dxf_line(x_br, y_b, x_tr, y_t, "STRUKTUR") # Kanan
        
        # 2. Gambar Air (Layer: AIR)
        dxf += dxf_line(x_wl, y_w, x_wr, y_w, "AIR")
        
        # 3. Dimensi Teks
        dxf += dxf_text(0, -0.5, f"b = {b}m", 0.2, "TEXT")
        dxf += dxf_text(x_tr + 0.5, H/2, f"H = {H}m", 0.2, "TEXT")
        dxf += dxf_text(0, y_w + 0.1, "MAT", 0.15, "TEXT")
        
        # Footer DXF
        dxf += "0\nENDSEC\n0\nEOF"
        
        return dxf

    # =========================================
    # 3. PARSHALL FLUME (ALAT UKUR DEBIT)
    # =========================================
    def hitung_parshall_flume(self, Q_input_m3s, lebar_leher_m=None):
        """
        Menghitung dimensi Parshall Flume atau Debit dari tinggi muka air.
        """
        # Rekomendasi Lebar Leher (W) berdasarkan Debit (USBR Standard)
        if lebar_leher_m is None:
            if Q_input_m3s < 0.03: W = 0.0762 # 3 inch
            elif Q_input_m3s < 0.11: W = 0.1524 # 6 inch
            elif Q_input_m3s < 0.25: W = 0.2286 # 9 inch
            elif Q_input_m3s < 0.45: W = 0.3048 # 1 ft
            elif Q_input_m3s < 1.00: W = 0.6096 # 2 ft
            elif Q_input_m3s < 2.50: W = 1.2192 # 4 ft
            else: W = 2.4384 # 8 ft (Besar)
        else:
            W = lebar_leher_m
            
        # Rumus Q = C * H^n (Metrik Aproksimasi)
        # Untuk W dalam meter, Q dalam m3/s, Rumus umum: Q = 2.3 * W * Ha^1.6
        # Kita balik rumusnya untuk cari H: Ha = (Q / (2.3 * W)) ^ (1/1.6)
        
        try:
            Ha = (Q_input_m3s / (2.25 * W)) ** (1/1.55) # Konstanta disesuaikan USBR Metric
        except:
            Ha = 0
            
        return {
            "Tipe": f"Parshall Flume W={W*100:.0f} cm",
            "Lebar_Leher_m": round(W, 3),
            "H_MukaAir_Hulu_m": round(Ha, 3),
            "Q_Max_Capacity": round(2.3 * W * (0.8**1.6), 2) # Asumsi H max 0.8m
        }
