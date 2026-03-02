# ==============================================================================
# 📄 NAMA FILE: libs_bps.py
# 📍 LOKASI: modules/cost/libs_bps.py
# 🛠️ FUNGSI: Membaca Centralized Cache dari Database Internal (Zero Latency)
# ==============================================================================

import pandas as pd
import sqlite3
import streamlit as st

class BPS_Database_Engine:
    """
    Engine Klien Pasif.
    Hanya mengeksekusi Query SQL ke database sentral. Tidak ada interaksi HTTP.
    Sesuai dengan arsitektur SaaS yang *scalable* dan anti-lag.
    """
    def __init__(self, db_path='enginex_core.db'):
        self.db_path = db_path

    def get_regional_prices(self, provinsi="Lampung"):
        """
        Menarik data seketika (instant fetch) dari SQLite.
        """
        try:
            # Buka koneksi statis ke database terpusat
            conn = sqlite3.connect(self.db_path)
            
            # Ambil data spesifik wilayah untuk klien yang sedang aktif
            query = "SELECT * FROM cache_harga_material WHERE provinsi = ?"
            df_cache = pd.read_sql(query, conn, params=(provinsi,))
            
            conn.close()
            
            if df_cache.empty:
                # Fallback proteksi jika Cron Job di server belum pernah berjalan
                st.warning(f"⚠️ Cache Harga Material untuk wilayah '{provinsi}' belum tersedia. Menunggu sinkronisasi Cron-Job oleh Administrator.")
                return pd.DataFrame()
                
            return df_cache

        except sqlite3.OperationalError:
            # Handle jika tabel belum dibuat oleh backend
            st.error("🚨 Kesalahan Sistem: Tabel 'cache_harga_material' tidak ditemukan di database. Hubungi Administrator.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Gagal membaca cache BPS: {e}")
            return pd.DataFrame()
