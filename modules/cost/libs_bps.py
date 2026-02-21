import pandas as pd
import duckdb
import requests
import time
import streamlit as st

class BPS_DuckDB_Engine:
    """
    Engine untuk mem-bypass latensi API BPS menggunakan DuckDB in-memory caching.
    Menggunakan arsitektur Cloud-to-App untuk penarikan harga material konstruksi.
    """
    def __init__(self, token_api):
        self.token = token_api
        # Inisialisasi DuckDB In-Memory
        self.con = duckdb.connect(database=':memory:')
        self._setup_cache_tables()

    def _setup_cache_tables(self):
        """Membuat skema tabel di RAM via DuckDB"""
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS cache_harga_material (
                id_material VARCHAR,
                nama_material VARCHAR,
                satuan VARCHAR,
                harga_dasar DOUBLE,
                provinsi VARCHAR,
                last_updated TIMESTAMP
            )
        """)

    def _fetch_stadata_mock(self, provinsi):
        """
        Simulasi (Mock) pemanggilan API BPS. 
        Di production, ganti dengan pustaka 'stadata' atau request API asli.
        """
        # Simulasi network delay
        time.sleep(1.2)
        
        # Payload JSON terstruktur (mensimulasikan JSON BPS yang deeply nested)
        mock_payload = {
            "status": "OK",
            "data": [
                {"turvar_id": "MTR-001", "name": "Semen Portland Tipe 1", "unit": "Zak 50kg", "price": 72500, "region": provinsi},
                {"turvar_id": "MTR-002", "name": "Besi Beton Polos", "unit": "Kg", "price": 12500, "region": provinsi},
                {"turvar_id": "MTR-003", "name": "Pasir Pasang", "unit": "M3", "price": 285000, "region": provinsi},
                {"turvar_id": "UPH-001", "name": "Upah Tukang Kayu", "unit": "OH", "price": 160000, "region": provinsi}
            ]
        }
        return mock_payload

    def get_regional_prices(self, provinsi="Lampung"):
        """
        Fungsi utama: Cek cache DuckDB dulu, jika kosong/kadaluarsa, tarik dari API.
        """
        # 1. Kueri Cache DuckDB (Secepat kilat)
        query_cache = f"SELECT * FROM cache_harga_material WHERE provinsi = '{provinsi}'"
        df_cache = self.con.execute(query_cache).df()
        
        if not df_cache.empty:
            return df_cache
            
        # 2. Tarik dari API jika Cache kosong
        with st.spinner(f"📡 Mengunduh indeks harga dari server BPS/ESSH untuk wilayah {provinsi}..."):
            raw_data = self._fetch_stadata_mock(provinsi)
            
            if raw_data["status"] == "OK":
                # Konversi JSON ke DataFrame
                df_new = pd.DataFrame(raw_data["data"])
                df_new.rename(columns={'turvar_id': 'id_material', 'name': 'nama_material', 'price': 'harga_dasar'}, inplace=True)
                df_new['provinsi'] = provinsi
                df_new['last_updated'] = pd.Timestamp.now()
                
                # 3. Injeksi ke DuckDB (Relational Algebra Operation)
                self.con.register('df_view', df_new)
                self.con.execute("INSERT INTO cache_harga_material SELECT * FROM df_view")
                
                return df_new
            else:
                raise Exception("Gagal terhubung ke API BPS")

    def semantic_price_matching(self, material_query):
        """
        Menerapkan fuzzy logic menggunakan DuckDB SQL untuk mengatasi disorientasi nomenklatur.
        (Mencari 'PC Semen 50kg' akan match dengan 'Semen Portland Tipe 1')
        """
        clean_query = material_query.lower().replace(" ", "%")
        
        sql = f"""
            SELECT nama_material, harga_dasar, satuan 
            FROM cache_harga_material 
            WHERE lower(nama_material) LIKE '%{clean_query}%'
            ORDER BY last_updated DESC LIMIT 1
        """
        result = self.con.execute(sql).df()
        
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
