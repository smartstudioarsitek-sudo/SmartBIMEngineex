# modules/utils/prompt_registry.py

def get_chain_prompts(category, project_name, data_context=""):
    """
    Mengembalikan skenario prompt berdasarkan Kategori Keahlian (Persona).
    """
    
    # === 1. MODUL STRUKTUR (libs_sni, libs_fem, libs_beton) ===
    if category == "STRUKTUR":
        return [
            f"""
            ROLE: Principal Structural Engineer. PROYEK: {project_name}.
            CONTEXT: {data_context}
            TUGAS 1 (BEBAN & GEMPA):
            1. Bab I Data Material (Mutu Beton fc', Baja fy) & Dimensi Preliminary.
            2. Bab II Analisis Beban (DL, LL per lantai). Buat Tabel Massa Bangunan Detail.
            3. Bab III Analisis Gempa (Respon Spektrum & Distribusi Fx Statik Ekivalen).
            """,
            """
            LANJUTKAN TUGAS 2 (DESAIN STRUKTUR ATAS):
            1. Bab IV Kombinasi Pembebanan (18 Kombinasi SNI).
            2. Bab V Desain Tulangan:
               - Balok (Cek Momen Kapasitas & Geser).
               - Kolom (Cek Strong Column Weak Beam).
            """,
            """
            LANJUTKAN TUGAS 3 (SUB-STRUKTUR & GAMBAR):
            1. Bab VI Pondasi (Hitung Jumlah Tiang, Efisiensi Grup, Desain Pilecap).
            2. Bab VII Script Python 'ezdxf' untuk menggambar denah pondasi & detail balok.
            """
        ]

    # === 2. MODUL SUMBER DAYA AIR (libs_hidrologi, libs_irigasi) ===
    elif category == "WATER":
        return [
            f"""
            ROLE: Senior Hydrologist & Dam Engineer. PROYEK: {project_name}.
            CONTEXT: {data_context}
            TUGAS 1 (HIDROLOGI):
            1. Bab I Analisis Curah Hujan Wilayah (Polygon Thiessen / Isohyet).
            2. Bab II Perhitungan Debit Banjir Rencana (Metode HSS Nakayasu/Snyder) untuk periode ulang 50 & 100 thn.
            """,
            """
            LANJUTKAN TUGAS 2 (HIDROLIKA BANGUNAN AIR):
            1. Bab III Desain Mercu Bendung (Tipe Ogee/Bulat). Hitung tinggi muka air banjir.
            2. Bab IV Desain Kolam Olak (Peredam Energi) tipe USBR/Vlughter.
            """,
            """
            LANJUTKAN TUGAS 3 (STABILITAS & GAMBAR):
            1. Bab V Analisis Stabilitas Bendung (Guling, Geser, Rembesan/Piping).
            2. Bab VI Script Python 'matplotlib'/'ezdxf' untuk menggambar penampang bendung.
            """
        ]

    # === 3. MODUL COST & ESTIMASI (libs_ahsp, libs_rab) ===
    elif category == "COST":
        return [
            f"""
            ROLE: Chief Quantity Surveyor (QS). PROYEK: {project_name}.
            CONTEXT: {data_context}
            TUGAS 1 (VOLUME & HARGA SATUAN):
            1. Bab I Breakdown Struktur Pekerjaan (WBS).
            2. Bab II Analisis Harga Satuan Pekerjaan (AHSP) mengacu SNI terbaru untuk Beton, Besi, Bekisting.
            """,
            """
            LANJUTKAN TUGAS 2 (PERHITUNGAN RAB):
            1. Bab III Take-off Volume (Estimasi volume item utama).
            2. Bab IV Rencana Anggaran Biaya (RAB) Rekapitulasi per Divisi.
            """,
            """
            LANJUTKAN TUGAS 3 (KURVA S & CASHFLOW):
            1. Bab V Bobot Pekerjaan & Durasi.
            2. Bab VI Tabel Rencana Cashflow & Script Python membuat Plot Kurva-S.
            """
        ]

    # === 4. MODUL ARSITEKTUR (libs_arch, libs_green) ===
    elif category == "ARSITEK":
        return [
            f"""
            ROLE: Principal Architect. PROYEK: {project_name}.
            CONTEXT: {data_context}
            TUGAS 1 (KONSEP & GUBAHAN):
            1. Bab I Analisis Tapak & Zoning (KDB, KLB, KDH).
            2. Bab II Konsep Gubahan Massa & Fasade (Tema Arsitektur).
            """,
            """
            LANJUTKAN TUGAS 2 (DENAH & MATERIAL):
            1. Bab III Program Ruang & Sirkulasi.
            2. Bab IV Spesifikasi Material Utama (Finishing) & Schedule Pintu/Jendela.
            """,
            """
            LANJUTKAN TUGAS 3 (GREEN BUILDING & GAMBAR):
            1. Bab V Analisis Green Building (OTTV, Efisiensi Energi, Rainwater Harvesting).
            2. Bab VI Script Python 'ezdxf' untuk generate Denah Layout sederhana.
            """
        ]
        
    # === 5. MODUL GEOTEKNIK (libs_geoteknik) ===
    elif category == "GEOTEK":
        return [
            f"""
            ROLE: Geotechnical Engineer. PROYEK: {project_name}.
            CONTEXT: {data_context}
            TUGAS 1 (STRATIGRAFI):
            1. Bab I Interpretasi Data Sondir (CPT) & Boring Log (N-SPT).
            2. Bab II Stratigrafi Tanah & Parameter Desain (c, phi, gamma).
            """,
            """
            LANJUTKAN TUGAS 2 (DAYA DUKUNG):
            1. Bab III Daya Dukung Pondasi Dangkal (Terzaghi/Meyerhof).
            2. Bab IV Daya Dukung Pondasi Dalam (Meyerhof/Luciano Decourt) Single Pile.
            """,
            """
            LANJUTKAN TUGAS 3 (PENURUNAN & LERENG):
            1. Bab V Analisis Penurunan (Settlement) Segera & Konsolidasi.
            2. Bab VI Analisis Stabilitas Lereng (jika ada) & Rekomendasi Akhir.
            """
        ]

    else:
        # Default fallback
        return [f"Buat laporan umum untuk proyek {project_name}."]
