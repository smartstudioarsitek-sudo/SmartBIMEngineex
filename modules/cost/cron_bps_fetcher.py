# ==============================================================================
# 📄 NAMA FILE: cron_bps_fetcher.py
# 🛠️ FUNGSI: Background Worker (ETL) untuk menarik API BPS secara Asinkron
# ⚠️ CARA PAKAI: Dijalankan oleh sistem operasi (Cron Job), BUKAN oleh Streamlit
# ==============================================================================

import sqlite3
import requests
import pandas as pd
from datetime import datetime
import time

# Konfigurasi Database Utama SaaS
DB_PATH = 'enginex_core.db'
BPS_API_TOKEN = "MASUKKAN_TOKEN_ASLI_BPS_DI_SINI"

def init_cache_table(cursor):
    """Menyiapkan tabel penampungan terpusat di SQLite"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cache_harga_material (
            id_material TEXT,
            nama_material TEXT,
            satuan TEXT,
            harga_dasar REAL,
            provinsi TEXT,
            sumber TEXT,
            last_updated TIMESTAMP
        )
    """)

def fetch_bps_data(provinsi="Lampung"):
    """
    Fungsi ini melakukan panggilan HTTP GET HTTP nyata ke Web API BPS.
    Di sini kita menyimulasikan parsing JSON dari payload BPS.
    """
    print(f"[{datetime.now()}] 📡 Menghubungi peladen BPS untuk wilayah {provinsi}...")
    
    # --- BLOK KODE ASLI API BPS (Disesuaikan dengan endpoint BPS 4.0) ---
    # headers = {'Authorization': f'Bearer {BPS_API_TOKEN}'}
    # url = f"https://webapi.bps.go.id/v1/api/interdomain/data/ikk?region={provinsi}"
    # response = requests.get(url, headers=headers)
    # data_json = response.json()
    
    # Karena ini simulasi untuk pengembangan, kita injeksi data bersih
    # yang merepresentasikan hasil ekstraksi dari BPS
    time.sleep(2) # Simulasi latensi jaringan yang tidak akan dirasakan user
    
    bps_data = [
        {"id_material": "BPS-001", "nama_material": "Semen Portland Tipe 1", "satuan": "kg", "harga_dasar": 1400, "provinsi": provinsi, "sumber": "API BPS Pusat"},
        {"id_material": "BPS-002", "nama_material": "Pasir Pasang", "satuan": "m3", "harga_dasar": 285000, "provinsi": provinsi, "sumber": "API BPS Pusat"},
        {"id_material": "BPS-003", "nama_material": "Bata Merah", "satuan": "bh", "harga_dasar": 850, "provinsi": provinsi, "sumber": "API BPS Pusat"},
        {"id_material": "BPS-004", "nama_material": "Pekerja (Tukang)", "satuan": "OH", "harga_dasar": 150000, "provinsi": provinsi, "sumber": "API BPS Pusat"}
    ]
    
    # Data ESSH lokal (Prioritas Timpaan)
    essh_data = [
        {"id_material": "ESH-001", "nama_material": "Semen Portland Tipe 1", "satuan": "kg", "harga_dasar": 1650, "provinsi": provinsi, "sumber": f"ESSH PUPR {provinsi}"},
        {"id_material": "ESH-002", "nama_material": "Besi Beton Polos", "satuan": "kg", "harga_dasar": 13500, "provinsi": provinsi, "sumber": f"ESSH PUPR {provinsi}"},
        {"id_material": "ESH-003", "nama_material": "Batu Kali", "satuan": "m3", "harga_dasar": 250000, "provinsi": provinsi, "sumber": f"ESSH PUPR {provinsi}"}
    ]

    # Proses ETL (Extract, Transform, Load) - Culling Duplikasi
    df_bps = pd.DataFrame(bps_data)
    df_essh = pd.DataFrame(essh_data)
    
    essh_materials = df_essh['nama_material'].str.lower().tolist()
    df_bps_filtered = df_bps[~df_bps['nama_material'].str.lower().isin(essh_materials)]
    
    df_final = pd.concat([df_essh, df_bps_filtered], ignore_index=True)
    df_final['last_updated'] = datetime.now()
    
    return df_final

def run_cron_job():
    """Fungsi utama yang dieksekusi oleh Task Scheduler/Cron"""
    try:
        print("==================================================")
        print(f"Memulai Sinkronisasi Database BPS Terpusat...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        init_cache_table(cursor)
        
        # Tarik data (Contoh untuk 1 wilayah, bisa di-loop untuk 38 Provinsi)
        df_target = fetch_bps_data("Lampung")
        
        # Hapus data usang untuk provinsi tersebut
        cursor.execute("DELETE FROM cache_harga_material WHERE provinsi = ?", ("Lampung",))
        
        # Injeksi data baru ke SQLite (Tersentralisasi)
        df_target.to_sql('cache_harga_material', conn, if_exists='append', index=False)
        
        conn.commit()
        conn.close()
        print(f"✅ Selesai! {len(df_target)} material berhasil diperbarui ke database lokal.")
        print("==================================================")
    except Exception as e:
        print(f"❌ Gagal mengeksekusi Cron Job: {e}")

if __name__ == "__main__":
    run_cron_job()
