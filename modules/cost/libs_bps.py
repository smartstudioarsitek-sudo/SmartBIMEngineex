import pandas as pd
import duckdb
import time
import streamlit as st

class BPS_DuckDB_Engine:
    """
    Engine Hybrid Penarikan Harga Material.
    Hierarki Prioritas: 1. ESSH PUPR (Lokal) -> 2. BPS (Nasional)
    """
    def __init__(self, token_api):
        self.token = token_api
        self.con = duckdb.connect(database=':memory:')
        self._setup_cache_tables()

    def _setup_cache_tables(self):
        """Membuat skema tabel di RAM via DuckDB dengan tambahan kolom SUMBER"""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS cache_harga_material (
                id_material VARCHAR,
                nama_material VARCHAR,
                satuan VARCHAR,
                harga_dasar DOUBLE,
                provinsi VARCHAR,
                sumber VARCHAR,
                last_updated TIMESTAMP
            )
        """)

    def get_regional_prices(self, provinsi="Lampung"):
        """
        Fungsi utama: Menarik data dengan hierarki ESSH prioritas utama.
        """
        query_cache = f"SELECT * FROM cache_harga_material WHERE provinsi = '{provinsi}'"
        df_cache = self.con.execute(query_cache).df()
        
        if not df_cache.empty:
            return df_cache
            
        with st.spinner(f"📡 Sinkronisasi Hierarki Harga: Memprioritaskan ESSH {provinsi} sebelum BPS..."):
            time.sleep(1.5) # Simulasi network delay
            
            # --- 1. MOCK DATA ESSH (PRIORITAS 1) ---
            essh_data = [
                {"id_material": "ESH-001", "nama_material": "Semen Portland Tipe 1", "satuan": "kg", "harga_dasar": 1650, "provinsi": provinsi, "sumber": f"ESSH PUPR {provinsi}"},
                {"id_material": "ESH-002", "nama_material": "Besi Beton Polos", "satuan": "kg", "harga_dasar": 13500, "provinsi": provinsi, "sumber": f"ESSH PUPR {provinsi}"},
                {"id_material": "ESH-003", "nama_material": "Batu Kali", "satuan": "m3", "harga_dasar": 250000, "provinsi": provinsi, "sumber": f"ESSH PUPR {provinsi}"}
            ]
            
            # --- 2. MOCK DATA BPS (PRIORITAS 2 - FALLBACK) ---
            bps_data = [
                # Semen ini HARUSNYA DIABAIKAN karena sudah ada di ESSH
                {"id_material": "BPS-001", "nama_material": "Semen Portland Tipe 1", "satuan": "kg", "harga_dasar": 1400, "provinsi": provinsi, "sumber": "API BPS Pusat"},
                # Bata dan Pasir MASUK karena tidak ada di ESSH
                {"id_material": "BPS-002", "nama_material": "Pasir Pasang", "satuan": "m3", "harga_dasar": 285000, "provinsi": provinsi, "sumber": "API BPS Pusat"},
                {"id_material": "BPS-003", "nama_material": "Bata Merah", "satuan": "bh", "harga_dasar": 850, "provinsi": provinsi, "sumber": "API BPS Pusat"},
                {"id_material": "BPS-004", "nama_material": "Pekerja (Tukang)", "satuan": "OH", "harga_dasar": 150000, "provinsi": provinsi, "sumber": "API BPS Pusat"}
            ]

            # --- LOGIKA PENGGABUNGAN (SMART FILTER) ---
            df_essh = pd.DataFrame(essh_data)
            df_bps = pd.DataFrame(bps_data)

            # Buat list nama material yang sudah dikunci oleh ESSH
            essh_materials = df_essh['nama_material'].str.lower().tolist()

            # Buang data BPS yang namanya bertabrakan dengan ESSH
            df_bps_filtered = df_bps[~df_bps['nama_material'].str.lower().isin(essh_materials)]

            # Gabungkan: ESSH di urutan atas, disusul BPS yang lolos filter
            df_final = pd.concat([df_essh, df_bps_filtered], ignore_index=True)
            df_final['last_updated'] = pd.Timestamp.now()
            
            # Urutkan kolom sesuai struktur DuckDB
            df_final = df_final[['id_material', 'nama_material', 'satuan', 'harga_dasar', 'provinsi', 'sumber', 'last_updated']]

            # Injeksi ke Memory RAM
            self.con.register('df_view', df_final)
            self.con.execute("INSERT INTO cache_harga_material SELECT * FROM df_view")
            
            return df_final
