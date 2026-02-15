import math

class RAB_Engine:
    
    def hitung_volume_terjunan_hybrid(self, H_total, B_saluran, n_trap=2):
        """
        Menghitung volume Terjunan Hybrid (Lantai Beton + Sayap Batu Kali).
        """
        H_per_trap = H_total / n_trap
        L_kolam = 2.0 * H_per_trap + 1.5
        L_total = n_trap * L_kolam
        
        # 1. Volume Beton (Lantai & Mercu)
        tebal_lt = 0.3
        vol_beton = (L_total * B_saluran * tebal_lt) + (n_trap * B_saluran * 0.4 * 0.4) # Mercu kecil
        
        # 2. Volume Batu Kali (Dinding Sayap)
        # Asumsi dinding trapesium: Lebar atas 0.3, Bawah 0.5, Tinggi rata2 (H+0.5)
        h_dinding = H_per_trap + 0.6 
        area_dinding = ((0.3 + 0.5)/2) * h_dinding
        vol_batu = 2 * (area_dinding * L_total) # Kiri Kanan
        
        # 3. Galian
        vol_galian = (vol_beton + vol_batu) * 1.3
        
        return {
            "Item": "Terjunan Hybrid Multi-Step",
            "Dimensi": f"{n_trap} Trap x {H_per_trap:.1f}m",
            "Volume": {
                "Beton_K225": round(vol_beton, 2),
                "Pasangan_Batu": round(vol_batu, 2),
                "Galian_Tanah": round(vol_galian, 2),
                "Besi_Polos": round(vol_beton * 80, 2) # 80kg/m3
            }
        }

    def hitung_volume_box_culvert(self, b, h, panjang):
        """Hitung Volume Precast/Cast-in-situ Box Culvert."""
        tebal = 0.20 # 20cm
        
        # Luas Penampang Beton
        area_outer = (b + 2*tebal) * (h + 2*tebal)
        area_inner = b * h
        area_beton = area_outer - area_inner
        
        vol_beton = area_beton * panjang
        berat_besi = vol_beton * 150 # 150 kg/m3 (Heavy reinforcement)
        
        return {
            "Item": f"Box Culvert {b}x{h}m",
            "Volume": {
                "Beton_K350": round(vol_beton, 2),
                "Besi_Ulir": round(berat_besi, 2),
                "Bekisting": round((2*b + 2*h) * panjang, 2) # Inner formwork only
            }
        }
