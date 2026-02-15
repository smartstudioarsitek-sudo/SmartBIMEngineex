import numpy as np
import math
import matplotlib.pyplot as plt

class Irrigation_Engine:
    
    def __init__(self):
        pass

    # =========================================
    # 1. DESAIN SALURAN (CORE LOGIC)
    # =========================================
    def hitung_dimensi_saluran(self, Q, b_ratio=1.5, m=1.0, S=0.0005, n=0.025):
        """
        Mencari dimensi saluran trapesium yang ekonomis secara iteratif.
        """
        # Inisialisasi variabel (Penting agar tidak return None)
        h = 0.1
        best_diff = float('inf')
        best_h = 0.1
        
        # Iterasi mencari tinggi air (h) sampai 10 meter
        while h < 15.0: # Naikkan batas iterasi untuk Q besar
            b = h * b_ratio # Lebar dasar proporsional
            
            # Properti Geometris
            A = (b + m * h) * h
            P = b + 2 * h * math.sqrt(1 + m**2)
            
            if P > 0:
                R = A / P
                # Rumus Manning: Q = (1/n) * A * R^(2/3) * S^(1/2)
                Q_calc = (1/n) * A * (R**(2/3)) * (S**0.5)
                
                # Cek selisih debit hitung vs debit target
                diff = abs(Q_calc - Q)
                
                # Simpan solusi terdekat (Best Fit)
                if diff < best_diff:
                    best_diff = diff
                    best_h = h
                
                # Jika sudah memenuhi atau melebihi target, stop
                if Q_calc >= Q: 
                    break
            
            h += 0.05
            
        # Gunakan best_h yang ditemukan untuk hitungan final
        h = best_h
        b = h * b_ratio
        
        # Hitung ulang parameter final untuk output
        A = (b + m * h) * h
        V = Q / A if A > 0 else 0
        T = b + 2 * m * h 
        D = A / T if T > 0 else 0
        Fr = V / math.sqrt(9.81 * D) if D > 0 else 0
        
        # Tinggi Jagaan (Freeboard) Standar KP-03
        if Q < 0.5: w = 0.20
        elif Q < 1.5: w = 0.20
        elif Q < 5.0: w = 0.25
        elif Q < 10.0: w = 0.30
        elif Q < 50.0: w = 0.60
        else: w = 0.75 # Untuk Q besar
        
        H_total = h + w
        
        # Status Keamanan Aliran
        status = "AMAN"
        warns = []
        if Fr >= 1.0: 
            status = "BAHAYA"
            warns.append("Aliran Superkritis")
        if V < 0.6: 
            status = "PERHATIAN"
            warns.append("Kecepatan Rendah (Endapan)")
        if V > 3.0:
            status = "BAHAYA"
            warns.append("Kecepatan Tinggi (Erosi)")
            
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
                "Area": round(A, 2)
            },
            "Status": status,
            "Catatan": ", ".join(warns) if warns else "Hidrolis OK"
        }

    # =========================================
    # [FIX] ALIAS / WRAPPER UNTUK AI
    # =========================================
    def hitung_dimensi_ekonomis(self, Q, S, n, m):
        """
        Wrapper Function: Menerima panggilan dari AI yang 'salah nama'
        dan meneruskannya ke fungsi utama 'hitung_dimensi_saluran'.
        """
        return self.hitung_dimensi_saluran(Q=Q, S=S, n=n, m=m)

    # =========================================
    # [FIX BARU] HITUNG DAN GAMBAR (PLOTTING)
    # =========================================
    def hitung_dan_gambar_saluran(self, Q, S, n, m):
        """
        Fungsi 'All-in-One' yang diminta AI: Hitung dimensi lalu return Figure Matplotlib.
        """
        # 1. Hitung Dimensi
        hasil = self.hitung_dimensi_saluran(Q, S=S, n=n, m=m)
        dim = hasil['Dimensi']
        
        b = dim['b']
        h = dim['h_air']
        H = dim['H_total']
        w = dim['w']
        
        # 2. Plotting Gambar
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Koordinat Saluran (Trapesium)
        # Kiri Atas -> Kiri Bawah -> Kanan Bawah -> Kanan Atas
        x_tanah = [-b/2 - m*H, -b/2, b/2, b/2 + m*H]
        y_tanah = [H, 0, 0, H]
        
        # Plot Tanah
        ax.plot(x_tanah, y_tanah, 'brown', lw=3, label='Saluran Tanah/Beton')
        ax.fill_between(x_tanah, y_tanah, -0.5, color='sienna', alpha=0.3)
        
        # Koordinat Air
        x_air = [-b/2 - m*h, -b/2, b/2, b/2 + m*h]
        y_air = [h, 0, 0, h]
        
        # Plot Air
        ax.plot(x_air, y_air, 'blue', lw=1.5, linestyle='--')
        ax.fill(x_air, y_air, 'cyan', alpha=0.5, label='Air Banjir')
        
        # Anotasi Dimensi
        ax.text(0, h/2, f"h = {h}m", ha='center', color='blue')
        ax.text(0, -0.3, f"b = {b}m", ha='center', fontweight='bold')
        ax.text(b/2 + m*H, H, f"Freeboard = {w}m", ha='left', fontsize=8)

        ax.set_title(f"Cross Section Saluran (Q={Q} m3/s)")
        ax.set_aspect('equal')
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        
        # Return Figure dan Info Dimensi (b & h)
        return fig, {"b": b, "h": h, "H": H}

    # =========================================
    # 3. GENERATOR GAMBAR CAD (.DXF)
    # =========================================
    def generate_dxf_script(self, desain_data_or_b, h_total=None, m=None, t=None, filename="out.dxf"):
        """
        Membuat string konten file .DXF sederhana.
        """
        if isinstance(desain_data_or_b, dict):
            data = desain_data_or_b
            b = data['Dimensi']['b']
            H = data['Dimensi']['H_total']
            h_air = data['Dimensi']['h_air']
            m = data['Dimensi']['m']
        else:
            b = desain_data_or_b
            H = h_total
            h_air = H - 0.6 if H else 1.0
            m = m if m is not None else 1.0
            
        # Koordinat Trapesium
        x_bl = -b/2; y_b = 0; x_br = b/2
        x_tl = -b/2 - (m*H); y_t = H; x_tr = b/2 + (m*H)
        x_wl = -b/2 - (m*h_air); y_w = h_air; x_wr = b/2 + (m*h_air)
        
        dxf = "0\nSECTION\n2\nENTITIES\n"
        def dxf_line(x1, y1, x2, y2, layer):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
        
        def dxf_text(x, y, text, height, layer):
            return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{height}\n1\n{text}\n"

        dxf += dxf_line(x_tl, y_t, x_bl, y_b, "STRUKTUR")
        dxf += dxf_line(x_bl, y_b, x_br, y_b, "STRUKTUR")
        dxf += dxf_line(x_br, y_b, x_tr, y_t, "STRUKTUR")
        dxf += dxf_line(x_wl, y_w, x_wr, y_w, "AIR")
        dxf += dxf_text(0, -0.5, f"b = {b:.2f}m", 0.2, "TEXT")
        dxf += dxf_text(0, y_w + 0.1, "MAT", 0.15, "TEXT")
        dxf += "0\nENDSEC\n0\nEOF"
        return dxf

    # =========================================
    # 4. PARSHALL FLUME
    # =========================================
    def hitung_parshall_flume(self, Q_input_m3s, lebar_leher_m=None):
        if lebar_leher_m is None:
            if Q_input_m3s < 0.03: W = 0.0762 
            elif Q_input_m3s < 0.11: W = 0.1524 
            elif Q_input_m3s < 0.25: W = 0.2286 
            elif Q_input_m3s < 0.45: W = 0.3048 
            elif Q_input_m3s < 1.00: W = 0.6096 
            elif Q_input_m3s < 2.50: W = 1.2192 
            else: W = 2.4384 
        else:
            W = lebar_leher_m
        try: Ha = (Q_input_m3s / (2.25 * W)) ** (1/1.55)
        except: Ha = 0
        return {
            "Tipe": f"Parshall Flume W={W*100:.0f} cm",
            "Lebar_Leher_m": round(W, 3),
            "H_MukaAir_Hulu_m": round(Ha, 3),
            "Q_Max_Capacity": round(2.3 * W * (0.8**1.6), 2)
        }
