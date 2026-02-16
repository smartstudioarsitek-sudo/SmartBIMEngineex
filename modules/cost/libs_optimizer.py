import pandas as pd
import numpy as np
import sys

# --- MEKANISME IMPORT ROBUST (Tahan Banting) ---
# Mencoba import dari folder modules, jika gagal import langsung dari root
try:
    from modules.struktur import libs_sni as sni
except ImportError:
    import libs_sni as sni

class BeamOptimizer:
    def __init__(self, fc, fy, harga_satuan):
        """
        Inisialisasi Optimizer.
        Input:
        - fc, fy: Mutu material
        - harga_satuan: Dictionary harga {'beton': x, 'baja': y, ...}
        """
        self.fc = fc
        self.fy = fy
        # Default harga jika tidak disediakan
        self.h_beton = harga_satuan.get('beton', 1100000)
        self.h_baja = harga_satuan.get('baja', 14000)
        self.h_bekisting = harga_satuan.get('bekisting', 150000)

    def cari_dimensi_optimal(self, Mu_kNm, bentang_m):
        """
        Mencari dimensi b x h yang paling murah namun Aman secara struktur.
        Returns: List of Dictionary (Top 5 opsi terbaik)
        """
        options = []
        
        # Range Lebar (b): 200mm s/d 600mm
        range_b = range(200, 650, 50)
        
        # Rule of thumb tinggi balok (L/12 s/d L/15) sebagai batas bawah pencarian
        h_min_rec = int(bentang_m * 1000 / 15) 
        # Range Tinggi (h): Mulai dari h_min s/d 1000mm
        range_h = range(max(300, h_min_rec), 1050, 50)
        
        # [CRITICAL FIX] Memanggil Class SNI 2019 yang BENAR (Sesuai file libs_sni.py)
        engine_sni = sni.SNI_Concrete_2019(self.fc, self.fy)

        # Loop Brute Force (Mencoba semua kombinasi ukuran)
        for b in range_b:
            for h in range_h:
                # Filter Geometri Wajar
                if h < b: continue # Balok pipih tidak disarankan untuk struktur utama
                if h > 3 * b: continue # Terlalu langsing (Bahaya tekuk lateral)
                
                # Estimasi tinggi efektif (d)
                ds = 40 + 10 + 6 # Selimut(40) + Sengkang(10) + 1/2 D_tulangan(6)
                d = h - ds
                
                try:
                    # Cek Kebutuhan Tulangan menggunakan Engine SNI
                    As_req = engine_sni.hitung_tulangan_perlu(Mu_kNm, d, b)
                except: 
                    continue
                
                # Cek Rasio Tulangan (Rho)
                rho = As_req / (b * d)
                
                # Filter Rho Wajar (Ekonomis)
                if rho > 0.025: continue # Maks 2.5% (Terlalu boros besi)
                if rho < 0.0018: continue # Min 0.18% (Minimum tulangan susut)
                
                # Hitung Estimasi Biaya per Meter Lari
                vol_beton = (b/1000) * (h/1000) * 1.0 # m3
                berat_baja = (As_req * 1.0 * 7850) / 1e6 * 1.3 # kg (Faktor 1.3 untuk overlap & tekuk)
                luas_bekisting = (2 * (h/1000)) + (b/1000) # m2 (Kiri + Kanan + Bawah)
                
                biaya = (vol_beton * self.h_beton) + (berat_baja * self.h_baja) + (luas_bekisting * self.h_bekisting)
                        
                options.append({
                    'b (mm)': b, 
                    'h (mm)': h, 
                    'As Perlu (mm2)': round(As_req, 2), 
                    'Biaya/m': int(biaya), 
                    'Rho (%)': round(rho * 100, 2)
                })
        
        # Jika tidak ada opsi yang memenuhi syarat
        if not options: return None
        
        # Urutkan berdasarkan Biaya Termurah (Ascending)
        df_opt = pd.DataFrame(options).sort_values(by='Biaya/m', ascending=True)
        
        # Kembalikan 5 opsi terbaik sebagai dictionary
        return df_opt.head(5).to_dict('records')
