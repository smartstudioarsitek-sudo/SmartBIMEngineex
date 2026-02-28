import sqlite3
import pandas as pd
import os
import json
from datetime import datetime
import io

class EnginexBackend:
    def __init__(self, db_path='enginex_core.db'):
        """
        Inisialisasi Backend Database.
        Mendukung sistem file 'Ephemeral' di Streamlit Cloud dengan failover ke /tmp
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Coba koneksi ke Database di lokasi utama
        try:
            self._connect_db(self.db_path)
        except sqlite3.OperationalError:
            # Jika gagal (biasanya karena permission Read-Only di Cloud), pindah ke /tmp
            print("⚠️ Read-Only Filesystem terdeteksi. Beralih ke folder sementara (/tmp)...")
            temp_path = os.path.join('/tmp', os.path.basename(db_path))
            self._connect_db(temp_path)
            self.db_path = temp_path

        self.init_db()

    def _connect_db(self, path):
        """Helper internal untuk melakukan koneksi ke SQLite"""
        # Pastikan folder tujuan ada
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def init_db(self):
        """Membuat tabel riwayat_konsultasi jika belum ada"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS riwayat_konsultasi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    project_name TEXT,
                    gem_name TEXT,
                    role TEXT,
                    content TEXT
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"❌ Error Init Database: {e}")

    # ==========================================
    # FITUR CHAT (CRUD)
    # ==========================================
    
    def simpan_chat(self, project, gem, role, text):
        """Menyimpan pesan baru ke database"""
        try:
            # Timestamp manual agar konsisten
            waktu_sekarang = datetime.now()
            
            self.cursor.execute(
                "INSERT INTO riwayat_konsultasi (tanggal, project_name, gem_name, role, content) VALUES (?, ?, ?, ?, ?)", 
                (waktu_sekarang, project, gem, role, text)
            )
            self.conn.commit()
        except Exception as e: 
            print(f"❌ Error Simpan Chat: {e}")

    def get_chat_history(self, project, gem):
        """Mengambil riwayat chat berdasarkan Proyek & Ahli"""
        try:
            query = "SELECT role, content FROM riwayat_konsultasi WHERE project_name = ? AND gem_name = ? ORDER BY id ASC"
            # Menggunakan pandas untuk keamanan query & kemudahan format
            df = pd.read_sql(query, self.conn, params=(project, gem))
            
            # Konversi ke format list of dicts yang diminta Streamlit
            return df.to_dict(orient='records')
        except Exception as e:
            print(f"⚠️ Gagal load history: {e}")
            return []

    def clear_chat(self, project, gem):
        """Menghapus chat spesifik (Reset Sesi)"""
        try:
            self.cursor.execute("DELETE FROM riwayat_konsultasi WHERE project_name = ? AND gem_name = ?", (project, gem))
            self.conn.commit()
        except Exception as e:
            print(f"❌ Error Clear Chat: {e}")

    def daftar_proyek(self):
        """List semua nama proyek unik yang ada di database"""
        try:
            df = pd.read_sql("SELECT DISTINCT project_name FROM riwayat_konsultasi", self.conn)
            if not df.empty:
                return df['project_name'].tolist()
            return []
        except: 
            return []

    # ==========================================
    # FITUR MANAJEMEN DATA (BACKUP & RESTORE)
    # ==========================================

    def export_data(self):
        """Export semua data ke format JSON String untuk Backup"""
        try:
            df = pd.read_sql("SELECT * FROM riwayat_konsultasi", self.conn)
            # Konversi datetime ke string agar valid JSON
            if 'tanggal' in df.columns:
                df['tanggal'] = df['tanggal'].astype(str)
                
            return df.to_json(orient='records', date_format='iso')
        except Exception as e: 
            return json.dumps({"error": str(e)})

    def import_data(self, json_file):
        """Restore data dari file JSON yang diupload user"""
        try:
            # 1. Baca File JSON
            data = json.load(json_file)
            
            # 2. Validasi Data Kosong
            if not data:
                return False, "⚠️ File JSON kosong atau format salah."

            # 3. Hapus Database Lama (Clean Slate) - Agar tidak duplikat
            self.cursor.execute("DELETE FROM riwayat_konsultasi")
            
            # 4. Proses DataFrame
            df = pd.DataFrame(data)
            
            # Buang kolom ID lama agar Auto-Increment baru bekerja
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            
            # PENTING: Fix Format Tanggal
            if 'tanggal' in df.columns:
                df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
            
            # 5. Masukkan ke SQL
            df.to_sql('riwayat_konsultasi', self.conn, if_exists='append', index=False)
            
            self.conn.commit()
            return True, f"✅ Sukses Restore! {len(df)} pesan dikembalikan."
            
        except Exception as e:
            # Rollback jika gagal di tengah jalan
            self.conn.rollback()
            return False, f"❌ Gagal Restore: {str(e)}"
    # ==========================================
    # MODUL SAAS: MANAJEMEN DATABASE AHSP (SUPER EXTRACTOR)
    # ==========================================
    def proses_dan_simpan_multi_excel(self, list_file_excel):
        """Membaca banyak file Excel, mengekstrak Sheet HSP, dan menggabungkannya"""
        import pandas as pd
        import streamlit as st
        
        semua_data = []
        
        try:
            for file in list_file_excel:
                # Baca semua sheet dalam 1 file excel
                xls = pd.ExcelFile(file)
                
                for sheet_name in xls.sheet_names:
                    # KITA HANYA INCAR SHEET YANG MENGANDUNG KATA "HSP"
                    if "HSP" in sheet_name.upper():
                        # Baca sheet mentah
                        df_raw = pd.read_excel(xls, sheet_name=sheet_name)
                        
                        # ALGORITMA PENCARI HEADER (Karena baris judul tiap Excel beda-beda)
                        header_row_idx = None
                        for i, row in df_raw.iterrows():
                            # Cari baris yang mengandung kata 'Uraian' dan 'Harga'
                            row_str = str(row.values).lower()
                            if 'uraian' in row_str and ('harga' in row_str or 'satuan' in row_str):
                                header_row_idx = i
                                break
                        
                        if header_row_idx is not None:
                            # Jadikan baris tersebut sebagai Header yang benar
                            df_bersih = pd.read_excel(xls, sheet_name=sheet_name, header=header_row_idx + 1)
                            
                            # Bersihkan kolom yang tidak bernama (Unamed) dan baris kosong
                            df_bersih = df_bersih.loc[:, ~df_bersih.columns.str.contains('^Unnamed')]
                            df_bersih = df_bersih.dropna(subset=[df_bersih.columns[1]]) # Asumsi kolom 1 adalah Uraian
                            
                            # Tambahkan penanda asal sumber data
                            df_bersih['Kategori_Sumber'] = file.name.split('.')[1][:15] if len(file.name.split('.'))>1 else "Master"
                            
                            semua_data.append(df_bersih)

            if not semua_data:
                return False, "❌ Tidak ditemukan sheet bernama 'HSP' atau format tidak sesuai."

            # Gabungkan semua data dari 5 file menjadi 1 Tabel Raksasa
            df_final = pd.concat(semua_data, ignore_index=True)
            
            # Kunci ke Database SQLite secara permanen
            df_final.to_sql('master_ahsp', self.conn, if_exists='replace', index=False)
            
            return True, f"✅ Sukses! {len(df_final)} Item Pekerjaan dari {len(list_file_excel)} File berhasil disedot ke Database!"

        except Exception as e:
            return False, f"Terjadi kesalahan saat memproses Excel: {e}"

    def get_master_ahsp_permanen(self):
        """Memanggil database AHSP saat aplikasi pertama kali dibuka"""
        import pandas as pd
        try:
            df = pd.read_sql_query("SELECT * FROM master_ahsp", self.conn)
            return df
        except Exception:
            return pd.DataFrame()
    def close(self):
        """Tutup koneksi database"""
        if self.conn:
            self.conn.close()

