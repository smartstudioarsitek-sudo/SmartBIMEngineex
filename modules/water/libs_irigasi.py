import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class Irrigation_Engine:
    def __init__(self):
        pass

    def hitung_dan_gambar_saluran(self, Q, S, n=0.015, m=1.0):
        """
        1. Menghitung dimensi ekonomis.
        2. Mengembalikan object Gambar (Figure) untuk ditampilkan AI.
        """
        # --- A. LOGIKA HITUNGAN (Otak Hydro Planner) ---
        # Rumus Manning: Q = A * (1/n) * R^(2/3) * S^(1/2)
        # Mencari lebar dasar (b) dan tinggi air (h) optimal
        # Simplifikasi: b = h (biar mendekati hidrolis terbaik untuk trapesium m=1)
        
        target_found = False
        h_desain = 0.5
        b_desain = 0.5
        
        # Iterasi mencari h yang pas
        for h in np.arange(0.1, 5.0, 0.05):
            b = h # Asumsi b = h
            A = (b + m * h) * h
            P = b + 2 * h * np.sqrt(1 + m**2)
            R = A / P
            Q_calc = (1/n) * A * (R**(2/3)) * (S**0.5)
            
            if Q_calc >= Q:
                h_desain = h
                b_desain = b
                target_found = True
                break
        
        if not target_found:
            return None, "Debit terlalu besar, butuh dimensi khusus."

        # Tinggi Jagaan (Freeboard) - Standar KP-03
        w = 0.6 if Q > 1.0 else 0.4
        H_total = h_desain + w
        
        # --- B. LOGIKA GAMBAR (Matplotlib) ---
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Koordinat Titik Tanah (Trapezoid)
        # Kiri Atas, Kiri Bawah, Kanan Bawah, Kanan Atas
        x_tanah = [
            0,                  # Kiri Atas
            m * H_total,        # Kiri Bawah
            m * H_total + b_desain, # Kanan Bawah
            2 * m * H_total + b_desain # Kanan Atas
        ]
        y_tanah = [H_total, 0, 0, H_total]
        
        # Plot Saluran (Garis Tanah)
        ax.plot(x_tanah, y_tanah, 'k-', linewidth=2, label='Tanah Asli')
        
        # Plot Air (Area Biru)
        # Koordinat permukaan air
        top_width_water = b_desain + 2 * m * h_desain
        x_air = [
            m * (H_total - h_desain) + (m * h_desain), # Salah hitung dikit di koordinat visual, kita simplifikasi:
            m * H_total,        # Kiri Bawah Air
            m * H_total + b_desain, # Kanan Bawah Air
            m * H_total + b_desain  # Kanan Atas Air (perlu offset m)
        ]
        
        # Menggunakan Fill Polygon untuk Air
        x_poly = [
            m * (H_total - h_desain),           # Kiri Atas Air
            m * H_total,                        # Kiri Bawah
            m * H_total + b_desain,             # Kanan Bawah
            m * H_total + b_desain + m*h_desain # Kanan Atas Air
        ]
        y_poly = [h_desain, 0, 0, h_desain]
        
        polygon = patches.Polygon(list(zip(x_poly, y_poly)), closed=True, facecolor='#00BFFF', alpha=0.6, label='Air Irigasi')
        ax.add_patch(polygon)

        # Anotasi Dimensi
        ax.text(sum(x_tanah)/len(x_tanah), -0.2, f"b = {b_desain:.2f} m", ha='center')
        ax.text(x_poly[2] + 0.2, h_desain/2, f"h = {h_desain:.2f} m", color='blue')
        ax.text(x_tanah[3], H_total, f"H = {H_total:.2f} m", va='bottom')

        ax.set_title(f"DESAIN PENAMPANG SALURAN (Q = {Q} m3/s)")
        ax.set_aspect('equal')
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend()
        
        # Data Teks untuk Laporan
        info = {
            "b": b_desain,
            "h": h_desain,
            "w": w,
            "V_ijin": Q / ((b_desain + m*h_desain)*h_desain)
        }
        
        return fig, info