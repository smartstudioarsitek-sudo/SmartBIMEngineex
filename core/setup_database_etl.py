import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, String, Numeric, Text, ForeignKey
from sqlalchemy.orm import declarative_base

# ==============================================================================
# 1. KONFIGURASI DATABASE
# ==============================================================================
# Jika Kakak sudah punya PostgreSQL, gunakan baris ini (hapus tanda pagarnya):
# DB_URL = "postgresql://username:password@localhost:5432/nama_database"

# Untuk ujicoba awal sekarang, kita gunakan SQLite lokal terlebih dahulu
# agar Kakak bisa langsung melihat hasilnya tanpa harus install server database:
DB_URL = "sqlite:///smartbim_database_v2.db"

engine = create_engine(DB_URL, echo=False)
Base = declarative_base()

# ==============================================================================
# 2. MERANCANG SKEMA TABEL DENGAN PYTHON (ORM)
# ==============================================================================
class MasterTenaga(Base):
    __tablename__ = 'tb_mst_tenaga'
    id_tenaga = Column(Integer, primary_key=True, autoincrement=True)
    kode_tenaga = Column(String(10), nullable=True)
    uraian_tenaga = Column(String(255), nullable=False, index=True)
    satuan = Column(String(20), nullable=False, default='OH')
    harga_dasar = Column(Numeric(15, 2), nullable=False, default=0)

class MasterBahan(Base):
    __tablename__ = 'tb_mst_bahan'
    id_bahan = Column(Integer, primary_key=True, autoincrement=True)
    uraian_bahan = Column(String(255), nullable=False, index=True)
    satuan = Column(String(20), nullable=False)
    harga_dasar = Column(Numeric(15, 2), nullable=False, default=0)

class MasterAlat(Base):
    __tablename__ = 'tb_mst_alat'
    id_alat = Column(Integer, primary_key=True, autoincrement=True)
    uraian_alat = Column(String(255), nullable=False)
    satuan = Column(String(20), nullable=False)
    harga_dasar = Column(Numeric(15, 2), nullable=False, default=0)

class AHSPHeader(Base):
    __tablename__ = 'tb_ahsp_header'
    id_ahsp = Column(Integer, primary_key=True, autoincrement=True)
    kode_analisa = Column(String(50), nullable=False, index=True)
    uraian_pekerjaan = Column(Text, nullable=False)
    satuan = Column(String(20), nullable=False)
    divisi_pupr = Column(String(50))

class AHSPKomposisi(Base):
    __tablename__ = 'tb_rel_ahsp_komposisi'
    id_rel = Column(Integer, primary_key=True, autoincrement=True)
    id_ahsp = Column(Integer, ForeignKey('tb_ahsp_header.id_ahsp', ondelete="CASCADE"))
    tipe_sumber_daya = Column(String(10)) # 'TENAGA', 'BAHAN', atau 'ALAT'
    id_sumber_daya = Column(Integer, nullable=False)
    koefisien = Column(Numeric(10, 4), nullable=False)

# Memerintahkan Python untuk menciptakan tabel-tabel di atas ke dalam Database
print("Menciptakan skema tabel di database...")
Base.metadata.create_all(engine)
print("Skema tabel berhasil dibuat!")

# ==============================================================================
# 3. PROSES ETL (Menyedot Data CSV HSD ke Tabel Master)
# ==============================================================================
def run_etl_master_hsd(csv_path):
    print(f"\nMembaca file CSV: {csv_path}...")
    try:
        df = pd.read_csv(csv_path, skiprows=3)
    except Exception as e:
        print(f"Gagal membaca file: {e}")
        return

    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    kategori_saat_ini = None
    data_tenaga, data_bahan, data_alat = [], [], []
    
    for index, row in df.iterrows():
        no_val = str(row.get('NO.', '')).strip()
        uraian = str(row.get('URAIAN', '')).strip()
        
        if no_val == 'A.': kategori_saat_ini = 'TENAGA'; continue
        elif no_val == 'B.': kategori_saat_ini = 'BAHAN'; continue
        elif no_val == 'C.': kategori_saat_ini = 'ALAT'; continue
            
        harga = pd.to_numeric(row.get('HARGA', np.nan), errors='coerce')
        if pd.notna(harga) and uraian not in ['nan', '']:
            uraian_bersih = uraian.replace('\n', ' ')
            satuan = str(row.get('SATUAN', '')).strip()
            kode = str(row.get('KODE', '')).strip() if pd.notna(row.get('KODE')) else None
            
            row_dict = {'satuan': satuan, 'harga_dasar': harga}
            
            if kategori_saat_ini == 'TENAGA':
                row_dict['uraian_tenaga'] = uraian_bersih
                row_dict['kode_tenaga'] = kode if kode != 'nan' else None
                data_tenaga.append(row_dict)
            elif kategori_saat_ini == 'BAHAN':
                row_dict['uraian_bahan'] = uraian_bersih
                data_bahan.append(row_dict)
            elif kategori_saat_ini == 'ALAT':
                row_dict['uraian_alat'] = uraian_bersih
                data_alat.append(row_dict)

    # Konversi ke DataFrame
    df_tenaga = pd.DataFrame(data_tenaga)
    df_bahan = pd.DataFrame(data_bahan)
    df_alat = pd.DataFrame(data_alat)

    # Mengunggah data ke Database
    print(f"Mengunggah {len(df_tenaga)} data Tenaga Kerja...")
    df_tenaga.to_sql('tb_mst_tenaga', engine, if_exists='append', index=False)
    
    print(f"Mengunggah {len(df_bahan)} data Bahan Material...")
    df_bahan.to_sql('tb_mst_bahan', engine, if_exists='append', index=False)
    
    print(f"Mengunggah {len(df_alat)} data Peralatan...")
    df_alat.to_sql('tb_mst_alat', engine, if_exists='append', index=False)
    
    print("\n✅ PROSES ETL SELESAI! Seluruh data master telah masuk ke database.")

if __name__ == "__main__":
    # Pastikan nama file ini sesuai dengan file HSD yang Kakak miliki di folder yang sama
    csv_file = "1. AHS 182 PRSPN, STR,ARS.xlsx - HSD PSPN,STR,ARS.csv"
    run_etl_master_hsd(csv_file)
