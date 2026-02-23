import pandas as pd

class AHSP_Engine:
    def __init__(self):
        # ======================================================
        # 1. BIDANG CIPTA KARYA (GEDUNG & PERMUKIMAN)
        # ======================================================
        self.koefisien_ck = {
            "galian_tanah_manual": {
                "desc": "[CK-Gedung] 1 m3 Galian Tanah Biasa Kedalaman 1 m",
                "bahan": {}, 
                "upah": {"Pekerja": 0.750, "Mandor": 0.025}
            },
            "beton_k300": {
                "desc": "[CK-Gedung] 1 m3 Membuat Beton Mutu f’c = 26,4 MPa (K 300)",
                "bahan": {"Semen (kg)": 413, "Pasir (m3)": 0.48, "Split (m3)": 0.77},
                "upah": {"Pekerja": 1.65, "Tukang": 0.275, "Mandor": 0.083}
            },
            "papan_nama_proyek": {
                "desc": "[CK-Gedung] Pembuatan 1 Buah Papan Nama Proyek",
                "bahan": {"Multiplek 9 mm (Lbr)": 0.18, "Kayu Kaso (m3)": 0.011, "Paku (Kg)": 0.10, "Cat Minyak (Kg)": 0.20},
                "upah": {"Pekerja": 0.750, "Tukang": 0.750, "Mandor": 0.075}
            }
        }

        # ======================================================
        # 2. BIDANG BINA MARGA (JALAN & JEMBATAN)
        # ======================================================
        self.koefisien_bm = {
            "galian_tanah_alat": {
                "desc": "[BM-Jalan] 1 m3 Galian Biasa (Alat Berat)",
                "bahan": {"Sewa Excavator (Jam)": 0.056, "Sewa Dump Truck (Jam)": 0.092},
                "upah": {"Pekerja": 0.014, "Mandor": 0.005}
            },
            "beton_k300_jalan": {
                "desc": "[BM-Jembatan] 1 m3 Beton Struktur fc' 25 MPa (K-300)",
                "bahan": {"Semen (kg)": 400, "Pasir (m3)": 0.45, "Split (m3)": 0.75},
                "upah": {"Pekerja": 1.20, "Tukang": 0.20, "Mandor": 0.05} 
            }
        }

        # ======================================================
        # 3. BIDANG SUMBER DAYA AIR (IRIGASI, BENDUNG, JIAT)
        # ======================================================
        self.koefisien_sda = {
            "galian_tanah_manual_sda": {
                "desc": "[SDA-Irigasi] 1 m3 Galian Tanah Biasa (Saluran)",
                "bahan": {},
                "upah": {"Pekerja": 0.526, "Mandor": 0.052}
            },
            "beton_k225_sda": {
                "desc": "[SDA-Bendung] 1 m3 Beton Mutu fc' = 19,3 MPa (K 225)",
                "bahan": {"Semen (kg)": 371, "Pasir (m3)": 0.498, "Split (m3)": 0.77},
                "upah": {"Pekerja": 1.50, "Tukang": 0.25, "Mandor": 0.075}
            }
        }

        # ======================================================
        # [PENYELAMAT EXPORT EXCEL]
        # Menggabungkan ketiganya ke dalam variabel utama yang dicari oleh libs_export.py
        # ======================================================
        self.koefisien = {**self.koefisien_ck, **self.koefisien_bm, **self.koefisien_sda}

    def hitung_hsp(self, kode_analisa, harga_bahan_dasar, harga_upah_dasar, bidang="Cipta Karya"):
        """
        Kecerdasan Pemilihan Koefisien berdasarkan Bidang Proyek
        """
        # 1. Tentukan kamus mana yang mau dipakai
        if bidang == "Bina Marga":
            db_aktif = self.koefisien_bm
        elif bidang == "Sumber Daya Air":
            db_aktif = self.koefisien_sda
        else:
            db_aktif = self.koefisien_ck

        # 2. Fallback Logic: Cari kecocokan kata
        target_kode = kode_analisa
        if kode_analisa not in db_aktif: 
            for key in db_aktif.keys():
                if key.split('_')[0] in kode_analisa:
                    target_kode = key
                    break
            # Jika tetap tidak ketemu di bidang spesifik, cari di kamus gabungan (self.koefisien)
            if target_kode not in db_aktif:
                if target_kode in self.koefisien:
                    db_aktif = self.koefisien
                else:
                    return 0 
            
        data = db_aktif[target_kode]
        total_bahan = 0
        total_upah = 0
        
        # 3. Eksekusi Perhitungan
        for item, koef in data['bahan'].items():
            key_clean = item.split(" (")[0].lower()
            h_satuan = 0
            if "semen" in key_clean: h_satuan = harga_bahan_dasar.get('semen', 0)
            elif "pasir" in key_clean: h_satuan = harga_bahan_dasar.get('pasir beton', 0) # Sesuaikan dengan penamaan BPS
            elif "split" in key_clean: h_satuan = harga_bahan_dasar.get('kerikil', 0)
            elif "excavator" in key_clean: h_satuan = harga_bahan_dasar.get('sewa excavator', 500000)
            else: h_satuan = harga_bahan_dasar.get(key_clean, 0)
            
            total_bahan += koef * h_satuan
            
        for item, koef in data['upah'].items():
            h_upah = harga_upah_dasar.get(item.lower(), 0)
            total_upah += koef * h_upah
            
        return total_bahan + total_upah
