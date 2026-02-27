# ==============================================================================
# 📄 NAMA FILE: libs_legal.py
# 📍 LOKASI: modules/legal/libs_legal.py
# 🛠️ FUNGSI: Administrasi Kontrak, Draft SPK, RKK, & Evaluasi Tender
# ==============================================================================

import pandas as pd
from datetime import datetime, timedelta

class Legal_Contract_Engine:
    def __init__(self):
        self.engine_name = "SmartBIM Legal & Contract Engine (Perpres Pengadaan)"
        # Standar kewajaran harga: Penawaran tidak boleh > 100% OE, atau terlalu rendah (< 80% OE) tanpa klarifikasi
        self.batas_atas_wajar = 1.00
        self.batas_bawah_wajar = 0.80

    # ==========================================
    # 1. EVALUASI TENDER (KEWAJARAN HARGA)
    # ==========================================
    def evaluasi_kewajaran_harga(self, df_oe, df_penawaran_kontraktor):
        """
        Membandingkan Owner Estimate (OE/HPS) dengan Penawaran Kontraktor.
        Input: DataFrame OE dan DataFrame Penawaran (harus memiliki kolom 'Nama Pekerjaan' dan 'Total Harga')
        Output: DataFrame hasil evaluasi dan rekomendasi kelulusan.
        """
        try:
            # Menggabungkan data berdasarkan Nama Pekerjaan
            df_eval = pd.merge(df_oe, df_penawaran_kontraktor, on="Nama Pekerjaan", suffixes=('_OE', '_Penawaran'))
            
            # Kalkulasi Selisih dan Persentase
            df_eval['Selisih (Rp)'] = df_eval['Total Harga_Penawaran'] - df_eval['Total Harga_OE']
            df_eval['Rasio (%)'] = (df_eval['Total Harga_Penawaran'] / df_eval['Total Harga_OE']) * 100
            
            # Deteksi Kewajaran Item
            def cek_status(rasio):
                if rasio > 100:
                    return "🔴 GUGUR (Melebihi HPS)"
                elif rasio < 80:
                    return "🟡 KLARIFIKASI (Terlalu Rendah)"
                else:
                    return "🟢 WAJAR"
            
            df_eval['Status Evaluasi'] = df_eval['Rasio (%)'].apply(cek_status)
            
            # Evaluasi Total
            total_oe = df_eval['Total Harga_OE'].sum()
            total_penawaran = df_eval['Total Harga_Penawaran'].sum()
            rasio_total = (total_penawaran / total_oe) * 100
            
            rekomendasi = "TENDER DITERIMA"
            if rasio_total > 100:
                rekomendasi = "TENDER DITOLAK (Melebihi Total HPS)"
            elif rasio_total < 80:
                rekomendasi = "TAHAN (Wajib Klarifikasi Kewajaran Harga/Dumping)"

            return {
                "Total_OE_Rp": total_oe,
                "Total_Penawaran_Rp": total_penawaran,
                "Rasio_Penawaran_Total": round(rasio_total, 2),
                "Rekomendasi_Panitia": rekomendasi,
                "Detail_Evaluasi": df_eval
            }
        except Exception as e:
            return {"error": f"Gagal mengevaluasi tender: {str(e)}"}

    # ==========================================
    # 2. AUTO-DRAFTING SURAT PERINTAH KERJA (SPK)
    # ==========================================
    def draft_spk_pemerintah(self, nama_proyek, nama_kontraktor, nilai_kontrak, waktu_hari, ppk_nama):
        """
        Menghasilkan draft Surat Perintah Kerja (SPK) standar Perpres PBJ.
        """
        tanggal_sekarang = datetime.now()
        tanggal_selesai = tanggal_sekarang + timedelta(days=waktu_hari)
        
        draft = f"""
# SURAT PERINTAH KERJA (SPK)
**Nomor:** SPK/{tanggal_sekarang.strftime('%Y%m')}/001/PPK-BIM
**Tanggal:** {tanggal_sekarang.strftime('%d %B %Y')}

Paket Pekerjaan: **{nama_proyek.upper()}**

Yang bertanda tangan di bawah ini:
Nama: **{ppk_nama}**
Jabatan: Pejabat Pembuat Komitmen (PPK)
Selanjutnya disebut sebagai **PIHAK KESATU**.

Berdasarkan Surat Penetapan Pemenang, dengan ini memerintahkan:
Nama Perusahaan: **{nama_kontraktor.upper()}**
Selanjutnya disebut sebagai **PIHAK KEDUA**.

Untuk melaksanakan pekerjaan dengan syarat-syarat sebagai berikut:
1. **Harga Kontrak:** Sesuai dengan hasil evaluasi tender, nilai kontrak adalah sebesar **Rp {nilai_kontrak:,.2f}** (Sudah termasuk PPN 11% dan Biaya SMKK).
2. **Waktu Pelaksanaan:** Pekerjaan harus diselesaikan dalam waktu **{waktu_hari} hari kalender**, terhitung sejak tanggal SPK ini diterbitkan, dan harus diserahterimakan pada tanggal **{tanggal_selesai.strftime('%d %B %Y')}**.
3. **Standar Kualitas:** Pekerjaan wajib mengacu pada Spesifikasi Teknis, Rencana Kerja dan Syarat-syarat (RKS), serta model BIM 3D yang telah disepakati.

Demikian Surat Perintah Kerja ini dibuat untuk dilaksanakan dengan penuh tanggung jawab.

**PIHAK KEDUA** *(Penyedia Jasa)* [______________________]  

**PIHAK KESATU** *(Pejabat Pembuat Komitmen)* **{ppk_nama}**
"""
        return draft.strip()

    # ==========================================
    # 3. AUTO-DRAFTING RENCANA KESELAMATAN (RKK)
    # ==========================================
    def draft_rkk_dasar(self, nama_proyek, nilai_smkk):
        """
        Menghasilkan ringkasan RKK (Rencana Keselamatan Konstruksi) dari data RAB 5D.
        """
        draft = f"""
# RINGKASAN RENCANA KESELAMATAN KONSTRUKSI (RKK)
**Proyek:** {nama_proyek.upper()}

Berdasarkan Permen PUPR No. 10 Tahun 2021 tentang Pedoman SMKK, berikut adalah alokasi komitmen keselamatan proyek ini:

1. **Alokasi Biaya SMKK:** Telah dianggarkan secara spesifik sebesar **Rp {nilai_smkk:,.2f}** dalam RAB. Biaya ini tidak boleh dikurangi atau dialihkan untuk item pekerjaan fisik lainnya.
2. **Komponen Wajib (9 Item):**
   - Penyiapan RKK dan sosialisasi keselamatan.
   - Penyediaan APD (Alat Pelindung Diri) lengkap untuk seluruh pekerja.
   - Asuransi Kesehatan dan Ketenagakerjaan (BPJS).
   - Fasilitas kebersihan, kesehatan (P3K), dan ruang isolasi.
   - Rambu-rambu keselamatan dan barikade area bahaya.
3. **Sanksi Pelanggaran:** Kelalaian PIHAK KEDUA dalam mengimplementasikan komponen SMKK di atas akan mengakibatkan teguran tertulis hingga penghentian pekerjaan sementara tanpa kompensasi waktu.
"""
        return draft.strip()
