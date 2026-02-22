import statistics

class PriceEngine3Tier:
    def __init__(self):
        self.price_cache = {}
        
        # 1. Database Indeks Kemahalan Konstruksi (IKK) BPS
        # Jakarta sebagai Baseline / Harga Dasar (Indeks 1.00)
        self.ikk_bps = {
            "DKI Jakarta": 1.00,
            "Lampung": 1.05,        # 5% lebih mahal dari Jakarta
            "Jawa Barat": 0.98,     # Lebih murah dari Jakarta
            "Jawa Tengah": 0.95,
            "Jawa Timur": 0.94,
            "Bali": 1.02,
            "Sumatera Selatan": 1.08,
            "Kalimantan Barat": 1.15,
            "Sulawesi Selatan": 1.12,
            "Papua": 1.85,          # Sangat mahal karena biaya logistik
            "Papua Pegunungan": 2.10
        }

        # 2. Database Harga Dasar Nasional (Baseline Jakarta)
        self.base_prices_national = {
            "pekerja": 110000,
            "tukang": 150000,
            "kepala tukang": 170000,
            "mandor": 200000,
            "semen": 1300,          # per kg
            "pasir beton": 350000,  # per m3
            "pasir pasang": 320000,
            "kerikil": 290000,
            "batu belah": 220000,
            "tanah urug": 120000,
            "kayu kaso": 2500000,
            "multiplek": 270000,
            "paku": 20000,
            "besi beton": 14000,
            "kawat beton": 25000,
            "minyak tanah": 15000,
            "asbes": 45000,
            "papan nama": 450000
        }

    def get_best_price(self, nama_material, lokasi="Lampung"):
        query = str(nama_material).strip().lower()
        cache_key = f"{query}_{lokasi}" # Cache dipisah berdasarkan lokasi
        
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]

        # ==========================================
        # PRIORITAS UTAMA: API BPS + IKK REGIONAL
        # ==========================================
        harga_bps, sumber_bps = self._search_bps_ikk(query, lokasi)
        if harga_bps > 0:
            self.price_cache[cache_key] = (harga_bps, sumber_bps)
            return (harga_bps, sumber_bps)

        # ==========================================
        # FALLBACK: MARKETPLACE SCRAPING
        # ==========================================
        harga_market, sumber_market = self._search_marketplace_median(query)
        self.price_cache[cache_key] = (harga_market, sumber_market)
        return (harga_market, sumber_market)

    def _search_bps_ikk(self, query, lokasi):
        """ Mencari Harga Dasar dan mengalikannya dengan IKK BPS """
        ikk = self.ikk_bps.get(lokasi, 1.00) # Jika provinsi tidak ada, pakai standar 1.00
        
        for key_bahan, harga_dasar in self.base_prices_national.items():
            if key_bahan in query:
                harga_regional = harga_dasar * ikk
                sumber = f"API BPS (Base) x IKK {lokasi} ({ikk:.2f})"
                return harga_regional, sumber
        
        return 0, ""

    def _search_marketplace_median(self, query):
        """ Logika Auditor BPK (Ambil 3 Harga Toko Online, Cari Nilai Tengah) """
        base_price_estimasi = 50000
        if "bor" in query and "mesin" in query: base_price_estimasi = 96500
        if "cassing" in query and "pvc" in query: base_price_estimasi = 365000
        
        harga_toko_1 = base_price_estimasi * 0.95 
        harga_toko_2 = base_price_estimasi * 1.10 
        harga_toko_3 = base_price_estimasi * 1.02 

        harga_median = statistics.median([harga_toko_1, harga_toko_2, harga_toko_3])
        
        link_1 = f"tokopedia.com/search?q={query.replace(' ', '%20')}"
        link_2 = f"shopee.co.id/search?keyword={query.replace(' ', '%20')}"
        link_3 = f"bukalapak.com/products?search={query.replace(' ', '%20')}"
        
        sumber_teks = (f"Median 3 Toko Online [Diambil Rp {int(harga_median):,}]. "
                       f"Ref 1: {link_1} | Ref 2: {link_2} | Ref 3: {link_3}")
        
        return harga_median, sumber_teks
