import pandas as pd
from datetime import datetime

class Research_Engine:
    def __init__(self):
        # 1. DATABASE RANGE HARGA WAJAR (Update Q1 2026)
        # Ini berfungsi sebagai "Alarm" jika input harga terlalu murah/mahal
        self.market_price_range = {
            "semen_50kg": {"min": 63000, "max": 78000, "unit": "sak"},
            "besi_d10": {"min": 72000, "max": 95000, "unit": "btg"},
            "besi_d13": {"min": 115000, "max": 145000, "unit": "btg"},
            "pasir_pasang": {"min": 250000, "max": 350000, "unit": "m3"},
            "bata_merah": {"min": 600, "max": 900, "unit": "bh"},
            "beton_readymix_k300": {"min": 850000, "max": 1100000, "unit": "m3"},
            "tukang_harian": {"min": 130000, "max": 180000, "unit": "hari/org"}
        }

        # 2. DATABASE REGULASI DAERAH (Sample)
        self.regulasi_db = {
            "jakarta": {"kdb_max": 60, "klb_max": 2.4, "zona_gempa": "Sedang-Tinggi", "perda": "Pergub DKI No. 31/2022"},
            "surabaya": {"kdb_max": 65, "klb_max": 3.0, "zona_gempa": "Sedang", "perda": "Perwali Surabaya No. 52/2020"},
            "lampung": {"kdb_max": 70, "klb_max": 1.8, "zona_gempa": "Tinggi (Sumatra)", "perda": "Perda Kota Bandar Lampung No. 10/2011"},
            "bali": {"kdb_max": 40, "klb_max": 1.2, "tinggi_max": "15m (Pura)", "perda": "Perda Bali No. 16/2009"},
            "ikn": {"kdb_max": 50, "klb_max": 2.0, "konsep": "Forest City", "perda": "UU IKN No. 3/2022"}
        }

    def audit_kewajaran_harga(self, item_name, harga_input):
        """
        Mengecek apakah harga yang dimasukkan user/AI masuk akal.
        """
        item_key = item_name.lower().replace(" ", "_")
        
        # Coba cari partial match
        match = None
        for k, v in self.market_price_range.items():
            if k in item_key or item_key in k:
                match = v
                break
        
        if not match:
            return f"⚠️ DATA TIDAK DITEMUKAN: Tidak ada data pembanding untuk '{item_name}'. Lakukan survei manual."
            
        if harga_input < match['min']:
            deviasi = int((match['min'] - harga_input) / match['min'] * 100)
            return f"🚨 HARGA MENCURIGAKAN (Terlalu Murah): Rp {harga_input:,.0f} lebih rendah {deviasi}% dari pasar terendah (Rp {match['min']:,.0f}). Risiko kualitas rendah."
        
        elif harga_input > match['max']:
            deviasi = int((harga_input - match['max']) / match['max'] * 100)
            return f"⚠️ HARGA MENCURIGAKAN (Terlalu Mahal): Rp {harga_input:,.0f} lebih tinggi {deviasi}% dari pasar tertinggi (Rp {match['max']:,.0f}). Cek markup kontraktor."
            
        else:
            return f"✅ HARGA WAJAR: Masuk dalam range pasar (Rp {match['min']:,.0f} - Rp {match['max']:,.0f})."

    def deep_check_lokasi(self, lokasi):
        """
        Memberikan konteks regulasi & risiko bencana berdasarkan lokasi.
        """
        lokasi_lower = lokasi.lower()
        data = None
        
        for city, info in self.regulasi_db.items():
            if city in lokasi_lower:
                data = info
                break
        
        if not data:
            return "ℹ️ Lokasi belum ada di database DeepResearch. Gunakan aturan umum SNI."
            
        report = f"""
        [DEEP RESEARCH REPORT - LOKASI: {lokasi.upper()}]
        1. Regulasi Intensitas:
           - KDB Maks: {data.get('kdb_max')}%
           - KLB Maks: {data.get('klb_max')}
           - Referensi: {data.get('perda', 'Perda Setempat')}
           
        2. Risiko Lingkungan:
           - Zona Gempa: {data.get('zona_gempa')}
           - Batasan Khusus: {data.get('tinggi_max', 'Sesuai KKOP/Zonasi')}
        """
        return report

    def verifikasi_logika_proyek(self, luas_lahan, luas_bangunan, jumlah_lantai):
        """
        Cek apakah proyek ini masuk akal secara fisik (Logic Gate).
        """
        # 1. Cek Tapak
        tapak_bangunan = luas_bangunan / jumlah_lantai
        if tapak_bangunan > luas_lahan:
            return "❌ ERROR FATAL: Luas dasar bangunan melebihi luas tanah! Proyek mustahil dibangun."
        
        ratio = (tapak_bangunan / luas_lahan) * 100
        if ratio > 90:
            return f"⚠️ WARNING KRITIS: Bangunan menghabiskan {ratio:.1f}% lahan. Tidak ada sisa untuk sempadan/RTH. Rawan sengketa & banjir."
            
        return "✅ LOGIC PASS: Dimensi bangunan masuk akal terhadap lahan."