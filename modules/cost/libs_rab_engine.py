import math
import pandas as pd

class RAB_Engine:
    """
    Engine untuk menghitung Volume Fisik Bangunan Air.
    Output berupa Dictionary volume yang siap dikalikan dengan Harga Satuan.
    """
    
    def __init__(self):
        pass

    # =========================================
    # 1. SALURAN (BETON & BATU)
    # =========================================
    def hitung_volume_saluran_beton(self, b, h, m, panjang, tebal_cm=15):
        """
        Volume Saluran Beton Bertulang (U-Ditch / Trapesium).
        """
        t_m = tebal_cm / 100.0
        # Panjang keliling basah beton (Sisi miring + Dasar)
        sisi_miring = h * math.sqrt(1 + m**2)
        keliling_beton = b + (2 * sisi_miring)
        
        # 1. Volume Beton (m3)
        vol_beton = keliling_beton * t_m * panjang
        
        # 2. Volume Galian (m3) - Asumsi space kerja 20cm kiri kanan bawah
        lebar_galian_bawah = b + (2 * t_m) + 0.4
        tinggi_galian = h + t_m + 0.1
        lebar_galian_atas = lebar_galian_bawah + (2 * m * tinggi_galian)
        area_galian = ((lebar_galian_bawah + lebar_galian_atas) / 2) * tinggi_galian
        vol_galian = area_galian * panjang
        
        # 3. Besi Tulangan (kg) - Asumsi 100 kg/m3 beton (Tulangan Praktis/Ringan)
        berat_besi = vol_beton * 100.0
        
        # 4. Bekisting (m2) - Hanya sisi dalam dinding kiri kanan
        luas_bekisting = (2 * sisi_miring) * panjang
        
        return {
            "Item": f"Saluran Beton P={panjang}m",
            "Volume": {
                "Beton_K225": round(vol_beton, 2),
                "Galian_Tanah": round(vol_galian, 2),
                "Bekisting": round(luas_bekisting, 2),
                "Besi_Polos": round(berat_besi, 2)
            }
        }

    # =========================================
    # 2. TERJUNAN HYBRID (MULTI-STEP)
    # =========================================
    def hitung_volume_terjunan_hybrid(self, H_total, B_saluran, n_trap=2):
        """
        Menghitung volume Terjunan Hybrid (Lantai Beton + Sayap Batu Kali).
        H_total: Tinggi jatuh total (m)
        n_trap: Jumlah trap/undakan
        """
        H_per_trap = H_total / n_trap
        # Estimasi Panjang Kolam Olak per trap (USBR simplified: 2.5 x H)
        L_kolam = 2.5 * H_per_trap + 1.0
        L_total = n_trap * L_kolam
        
        # 1. Volume Beton (Lantai & Mercu)
        tebal_lt = 0.30 # 30cm lantai beton tahan gerusan
        vol_lantai = L_total * B_saluran * tebal_lt
        vol_mercu = n_trap * (B_saluran * 0.4 * 0.4) # Mercu kecil per trap
        vol_beton = vol_lantai + vol_mercu
        
        # 2. Volume Batu Kali (Dinding Sayap Kiri Kanan)
        # Asumsi dinding trapesium: Lebar atas 0.3, Bawah 0.5, Tinggi rata2 (H+0.5)
        h_dinding_avg = H_per_trap + 0.5 
        area_dinding = ((0.3 + 0.5)/2) * h_dinding_avg
        vol_batu = 2 * (area_dinding * L_total) # Dikali 2 (Kiri Kanan)
        
        # 3. Galian
        vol_galian = (vol_beton + vol_batu) * 1.3
        
        return {
            "Item": "Terjunan Hybrid Multi-Step",
            "Dimensi": f"{n_trap} Trap x {H_per_trap:.1f}m (L Total={L_total:.1f}m)",
            "Volume": {
                "Beton_K225": round(vol_beton, 2),
                "Pasangan_Batu": round(vol_batu, 2),
                "Galian_Tanah": round(vol_galian, 2),
                "Besi_Polos": round(vol_beton * 80, 2), # 80kg/m3 untuk lantai
                "Plesteran": round(2 * L_total * h_dinding_avg, 2)
            }
        }

    # =========================================
    # 3. BOX CULVERT (GORONG-GORONG)
    # =========================================
    def hitung_volume_box_culvert(self, b, h, panjang):
        """
        Hitung Volume Precast/Cast-in-situ Box Culvert.
        """
        tebal = 0.20 # Tebal dinding 20cm
        
        # Luas Penampang Beton
        area_outer = (b + 2*tebal) * (h + 2*tebal)
        area_inner = b * h
        area_beton = (area_outer - area_inner)
        
        vol_beton = area_beton * panjang
        berat_besi = vol_beton * 150.0 # 150 kg/m3 (Heavy reinforcement untuk beban jalan)
        
        # Bekisting (Hanya dalam, luar pakai galian rapi/bata)
        luas_bekisting = (2*b + 2*h) * panjang
        
        return {
            "Item": f"Box Culvert {b}x{h}m",
            "Volume": {
                "Beton_K350": round(vol_beton, 2), # Mutu tinggi
                "Besi_Ulir": round(berat_besi, 2),
                "Bekisting": round(luas_bekisting, 2),
                "Galian_Tanah": round(area_outer * panjang * 1.2, 2)
            }
        }
