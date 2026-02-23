import pandas as pd
import os

class AHSP_Engine:
    def __init__(self, db_path="Database_AHSP.xlsx"):
        """
        Engine AHSP Dinamis yang membaca file Excel, bukan Hardcode.
        """
        self.db_path = db_path
        
        # Penampung partisi 3 Bidang
        self.koefisien_ck = {}
        self.koefisien_bm = {}
        self.koefisien_sda = {}
        
        # Gabungan untuk fallback fallback parser AI
        self.koefisien = {} 

        self._load_database_from_excel()

    def _load_database_from_excel(self):
        """Membaca Excel dan menyusunnya ke dalam memori RAM."""
        if not os.path.exists(self.db_path):
            print(f"⚠️ Peringatan: File {self.db_path} tidak ditemukan. Engine AHSP kosong.")
            return
            
        try:
            # Baca file Excel
            df = pd.read_excel(self.db_path)
            
            # Menyusun ulang baris Excel menjadi Dictionary hierarkis
            for _, row in df.iterrows():
                bidang = str(row['Bidang']).strip().upper()
                kode = str(row['Kode_AHSP']).strip()
                desc = str(row['Deskripsi']).strip()
                kategori = str(row['Kategori']).strip().lower() # 'bahan', 'upah', atau 'alat'
                nama_komp = str(row['Nama_Komponen']).strip()
                sat = str(row['Satuan']).strip()
                koef = float(row['Koefisien'])
                
                # Arahkan ke partisi dictionary yang tepat
                target_dict = self.koefisien_ck
                if "SDA" in bidang: target_dict = self.koefisien_sda
                elif "BM" in bidang: target_dict = self.koefisien_bm

                # Inisialisasi struktur jika kode AHSP belum ada
                if kode not in target_dict:
                    target_dict[kode] = {"desc": desc, "bahan": {}, "upah": {}, "alat": {}}
                
                # Masukkan data ke dalam kategori yang tepat
                if "bahan" in kategori:
                    target_dict[kode]["bahan"][f"{nama_komp} ({sat})"] = koef
                elif "upah" in kategori:
                    target_dict[kode]["upah"][nama_komp] = koef
                elif "alat" in kategori:
                    target_dict[kode]["alat"][f"{nama_komp} ({sat})"] = koef

            # Gabungkan untuk keperluan fallback
            self.koefisien = {**self.koefisien_ck, **self.koefisien_bm, **self.koefisien_sda}
            
        except Exception as e:
            print(f"❌ Gagal memuat database AHSP: {e}")

    def hitung_hsp(self, kode_analisa, harga_bahan_dasar, harga_upah_dasar, bidang="Cipta Karya"):
        """
        Menghitung Harga Satuan Pekerjaan dengan mencocokkan data API harga ke koefisien.
        """
        # Pilih partisi database sesuai input bidang dari sidebar Streamlit
        if bidang == "Bina Marga": db_aktif = self.koefisien_bm
        elif bidang == "Sumber Daya Air": db_aktif = self.koefisien_sda
        else: db_aktif = self.koefisien_ck

        target_kode = kode_analisa
        # Fallback pencarian kode mirip
        if kode_analisa not in db_aktif: 
            for key in db_aktif.keys():
                if key.split('_')[0] in kode_analisa:
                    target_kode = key
                    break
            if target_kode not in db_aktif: return 0 
            
        data = db_aktif[target_kode]
        total_biaya = 0
        
        # Hitung Bahan
        for item, koef in data.get('bahan', {}).items():
            key_clean = item.split(" (")[0].lower()
            # Logic pencarian harga termurah dari API/BPS
            h_satuan = harga_bahan_dasar.get(key_clean, 0) 
            total_biaya += koef * h_satuan
            
        # Hitung Upah
        for item, koef in data.get('upah', {}).items():
            h_upah = harga_upah_dasar.get(item.lower(), 0)
            total_biaya += koef * h_upah

        # Hitung Alat
        for item, koef in data.get('alat', {}).items():
            key_clean = item.split(" (")[0].lower()
            h_alat = harga_bahan_dasar.get(key_clean, 0) # Menggunakan dictionary yang sama dengan bahan
            total_biaya += koef * h_alat
            
        return total_biaya
