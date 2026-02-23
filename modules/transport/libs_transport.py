# ==============================================================================
# 📄 NAMA FILE: libs_transport.py
# 📍 LOKASI: modules/transport/libs_transport.py
# 🛠️ FUNGSI: ANDALALIN, Geometrik Jalan Raya, & Tebal Perkerasan (Bina Marga)
# ==============================================================================

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

class Transport_Infrastructure_Engine:
    def __init__(self):
        self.engine_name = "SmartBIM Transport & ANDALALIN Engine (Standar Bina Marga)"

    # ==========================================
    # 1. ANALISIS DAMPAK LALU LINTAS (ANDALALIN)
    # ==========================================
    def hitung_bangkitan_lalin(self, fungsi_lahan, besaran_kapasitas):
        """
        Menghitung estimasi bangkitan perjalanan (Trip Generation) pada jam puncak.
        Standar ITE / Pedoman ANDALALIN Kemenhub.
        """
        # Trip rate assumptions (smp/jam/unit) - Satuan Mobil Penumpang
        trip_rates = {
            "Sekolah": 0.8,        # 0.8 smp per siswa/staf pada jam masuk/pulang
            "Perumahan": 0.5,      # 0.5 smp per unit rumah
            "Komersial": 2.5,      # 2.5 smp per 100 m2 luas lantai
            "Rumah Sakit": 1.5,    # 1.5 smp per tempat tidur
        }
        
        rate = trip_rates.get(fungsi_lahan, 1.0)
        
        if fungsi_lahan == "Komersial":
            total_trips = (besaran_kapasitas / 100) * rate
        else:
            total_trips = besaran_kapasitas * rate
            
        # Klasifikasi Wajib ANDALALIN (Permenhub No 17 Tahun 2021)
        if total_trips > 75:
            status = "🔴 WAJIB ANDALALIN DOKUMEN LENGKAP (Bangkitan Tinggi)"
        elif total_trips > 20:
            status = "🟡 ANDALALIN RINGAN / REKOMENDASI LALIN (Bangkitan Sedang)"
        else:
            status = "🟢 BEBAS ANDALALIN (Bangkitan Rendah)"
            
        return {
            "Fungsi_Lahan": fungsi_lahan,
            "Kapasitas_Input": besaran_kapasitas,
            "Estimasi_Bangkitan_smp_jam": round(total_trips, 2),
            "Status_Regulasi": status
        }

    # ==========================================
    # 2. DESAIN TEBAL PERKERASAN LENTUR (MDP BINA MARGA 2017)
    # ==========================================
    def desain_perkerasan_lentur(self, cbr_tanah_dasar_persen, cesa_pangkat_6):
        """
        Desain perkerasan lentur (Flexible Pavement) berdasarkan Manual Desain Perkerasan (MDP) Bina Marga 2017.
        cesa_pangkat_6 = Cumulative Equivalent Single Axle Load dalam juta (10^6).
        """
        # 1. Pengecekan Geoteknik Tanah Dasar
        if cbr_tanah_dasar_persen < 6:
            catatan_tanah = "⚠️ KRITIS: CBR < 6%. Wajib perbaikan tanah dasar (Stabilisasi Semen/Kapur atau Geotextile) setebal min. 300mm."
        else:
            catatan_tanah = "✅ AMAN: Tanah dasar memenuhi syarat (CBR >= 6%)."

        # 2. Pemilihan Struktur Lapisan (Simplifikasi Bagan Desain MDP 2017)
        if cesa_pangkat_6 <= 0.5:
            ac_wc = 40; ac_bc = 0; base_a = 150; subbase_b = 150
            tipe = "Lalu Lintas Rendah (Jalan Lokal/Akses)"
        elif cesa_pangkat_6 <= 4:
            ac_wc = 40; ac_bc = 60; base_a = 300; subbase_b = 0
            tipe = "Lalu Lintas Sedang (Jalan Kolektor)"
        elif cesa_pangkat_6 <= 10:
            ac_wc = 50; ac_bc = 60; base_a = 400; subbase_b = 0
            tipe = "Lalu Lintas Cukup Berat (Jalan Arteri Minor)"
        else:
            ac_wc = 50; ac_bc = 80; base_a = 500; subbase_b = 0
            tipe = "Lalu Lintas Berat (Jalan Nasional/Industri)"
            
        return {
            "Klasifikasi_Jalan": tipe,
            "Nilai_CBR_%": cbr_tanah_dasar_persen,
            "Beban_CESA_Juta": cesa_pangkat_6,
            "Lapis_Permukaan_AC_WC_mm": ac_wc,
            "Lapis_Antara_AC_BC_mm": ac_bc,
            "Lapis_Pondasi_Atas_LPA_KelasA_mm": base_a,
            "Lapis_Pondasi_Bawah_LPB_KelasB_mm": subbase_b,
            "Rekomendasi_Geoteknik": catatan_tanah
        }

    # ==========================================
    # 3. ALINYEMEN HORIZONTAL & SUPERELEVASI
    # ==========================================
    def desain_tikungan_horizontal(self, kecepatan_rencana_kmh, radius_lengkung_m):
        """
        Mengecek radius aman dan menghitung superelevasi (kemiringan melintang) tikungan.
        """
        e_max = 0.10 # Superelevasi maksimum (10%)
        # Faktor gesekan samping (f_max) secara empiris turun seiring naiknya kecepatan
        f_max = 0.15 - (kecepatan_rencana_kmh / 1000)
        
        # Rumus Jari-jari Minimum: Rmin = V^2 / 127(emax + fmax)
        r_min = (kecepatan_rencana_kmh ** 2) / (127 * (e_max + f_max))
        
        if radius_lengkung_m < r_min:
            status = f"❌ BAHAYA OVERTURNING: Radius rencana ({radius_lengkung_m}m) terlalu tajam. Radius minimal untuk {kecepatan_rencana_kmh} km/jam adalah {round(r_min, 2)}m."
            e_desain = e_max
        else:
            status = "✅ AMAN: Radius tikungan memenuhi syarat standar Bina Marga."
            # Perhitungan e_desain sederhana
            e_desain = (kecepatan_rencana_kmh ** 2) / (282 * radius_lengkung_m)
            # Dibatasi antara normal crown (2%) dan e_max (10%)
            e_desain = min(e_max, max(0.02, e_desain))

        return {
            "Kecepatan_Rencana_kmh": kecepatan_rencana_kmh,
            "Radius_Rencana_m": radius_lengkung_m,
            "Radius_Minimum_Aman_m": round(r_min, 2),
            "Superelevasi_Desain_%": round(e_desain * 100, 2),
            "Status_Keamanan": status
        }

    # ==========================================
    # 4. VISUALISASI PROFIL MELINTANG TIKUNGAN
    # ==========================================
    def gambar_profil_melintang(self, lebar_laju_m, superelevasi_persen):
        """
        Menggambar potongan melintang jalan (Cross-Section) pada daerah tikungan penuh (Full Superelevation).
        """
        e = superelevasi_persen / 100
        
        # Titik koordinat [X, Y]
        # X: Jarak dari sumbu jalan (As), Y: Elevasi (meter)
        x_kiri = -lebar_laju_m
        x_kanan = lebar_laju_m
        
        # Asumsi tikungan ke kanan, sisi kiri lebih tinggi, sisi kanan lebih rendah
        y_kiri = lebar_laju_m * e
        y_kanan = -lebar_laju_m * e

        fig = go.Figure()
        
        # Gambar aspal jalan
        fig.add_trace(go.Scatter(
            x=[x_kiri, 0, x_kanan], 
            y=[y_kiri, 0, y_kanan], 
            mode='lines+markers', 
            name='Permukaan Perkerasan', 
            line=dict(color='black', width=6),
            marker=dict(size=10, color='gold')
        ))
        
        # Gambar garis tengah (Centerline)
        fig.add_trace(go.Scatter(
            x=[0, 0], 
            y=[y_kanan - 0.5, y_kiri + 0.5], 
            mode='lines', 
            line=dict(color='red', dash='dashdot', width=2), 
            name='Sumbu Jalan (Centerline)'
        ))
        
        fig.update_layout(
            title=f"Profil Melintang Jalan - Full Superelevasi ({superelevasi_persen}%)",
            xaxis_title="Jarak dari Sumbu Jalan (Meter)",
            yaxis_title="Beda Tinggi Elevasi (Meter)",
            yaxis_range=[-1.0, 1.0],
            xaxis_range=[x_kiri - 1, x_kanan + 1],
            plot_bgcolor='aliceblue',
            hovermode="x unified"
        )
        return fig