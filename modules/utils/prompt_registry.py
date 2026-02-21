# modules/utils/prompt_registry.py

# ==============================================================================
# DOKTRIN KETAT UNTUK AI (MEMAKSA FORMAT DED/RKS & ANTI-LATEX)
# ==============================================================================
DOKTRIN_TPA = """
[INSTRUKSI MUTLAK & WAJIB DIPATUHI - FORMATTING]:
1. BERHENTI bertingkah seperti AI/Chatbot. JANGAN ADA kalimat pembuka/penutup. LANGSUNG cetak isi dokumen dengan bahasa Indonesia baku (EYD) layaknya Dokumen Kontrak Resmi.
2. SETIAP menyebutkan parameter atau metode pelaksanaan, WAJIB sertakan sitasi SNI (Contoh: "Berdasarkan SNI 2847:2019...", "Sesuai SNI 2052:2017...").
3. DILARANG KERAS MENGGUNAKAN SIMBOL LaTeX ($ atau $$) UNTUK RUMUS/SATUAN! Tulis dengan plain-text biasa (Misal tulis: "fc = 30 MPa", "luas lahan m2").
4. DILARANG MENGGUNAKAN TABEL MARKDOWN (|---|). Sajikan data dalam bentuk list (bullet/numbering) bertingkat yang rapi dan hierarkis (pasal demi pasal).
"""

def get_chain_prompts(category, project_name, data_context=""):
    """
    Mengembalikan skenario prompt berdasarkan Kategori Laporan.
    Didesain dengan metode Chaining (Berantai) agar AI menghasilkan dokumen komprehensif.
    """
    # === 1. MODUL STRUKTUR (DED) ===
    if category == "STRUKTUR":
        return [
            f"""{DOKTRIN_TPA}\nPROYEK: {project_name} | KONTEKS: {data_context}\nBAGIAN 1: Tulis 'BAB I. PENDAHULUAN & KRITERIA DESAIN STRUKTUR'. Jelaskan filosofi desain tahan gempa, list Standar Rujukan (SNI 1726:2019, 1727:2020, 2847:2019), dan Properti Material dalam plain text.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 2: Tulis 'BAB II. ANALISIS PEMBEBANAN GRAVITASI & ANGIN'. Rincikan Beban Mati, Beban Hidup sesuai SNI 1727:2020, dan kombinasi LRFD dalam format list.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 3: Tulis 'BAB III. ANALISIS KINERJA SEISMIK'. Jelaskan parameter Ss, S1, Fa, Fv, SDS, SD1 berdasarkan SNI 1726:2019 dan penetapan KDS D.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 4: Tulis 'BAB IV. EVALUASI PARAMETER DINAMIS STRUKTUR'. Jelaskan syarat Partisipasi Massa Ragam (>= 90%) dan Penskalaan Gaya Geser Dasar (V dinamik >= 100% V statik).""",
            f"""{DOKTRIN_TPA}\nBAGIAN 5: Tulis 'BAB V. DESAIN KAPASITAS PENAMPANG BETON BERTULANG'. Jelaskan kontrol 'Strong Column-Weak Beam' dan Desain Geser Kapasitas (Mpr).""",
            f"""{DOKTRIN_TPA}\nBAGIAN 6: Tulis 'BAB VI. KESIMPULAN AUDIT'. Berikan kesimpulan final kelayakan struktur dan buat list penandatangan."""
        ]
        
    # === 2. MODUL SUMBER DAYA AIR (DED) ===
    elif category == "WATER":
        return [
            f"""{DOKTRIN_TPA}\nPROYEK: {project_name}\nBAGIAN 1: Tulis 'BAB I. PENDAHULUAN & DAS' merujuk SNI 2415:2016.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 2: Tulis 'BAB II. ANALISIS HUJAN' jelaskan Log Pearson Tipe III.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 3: Tulis 'BAB III. HUJAN EFEKTIF' jelaskan metode NRCS Curve Number (CN).""",
            f"""{DOKTRIN_TPA}\nBAGIAN 4: Tulis 'BAB IV. HSS NAKAYASU' tuliskan parameter Tp, Tg, Qp dalam plain text.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 5: Tulis 'BAB V. KESIMPULAN' dan rekomendasi mitigasi banjir."""
        ]

    # === 3. MODUL SPESIFIKASI TEKNIS (RKS) - SIMBG REQUIREMENT ===
    elif category == "RKS":
        return [
            f"""{DOKTRIN_TPA}
            PROYEK: {project_name} | KONTEKS MUTU: {data_context}
            BAGIAN 1: Tulis 'BAB I. SYARAT-SYARAT UMUM & STANDAR REFERENSI'.
            - Uraikan lingkup pekerjaan struktur secara umum.
            - Buat daftar peraturan baku dan standar nasional yang wajib dipatuhi kontraktor (SNI Beton, Baja, Gempa, ASTM).
            - Jelaskan kewajiban kontraktor terkait persetujuan material (Material Approval) sebelum pelaksanaan.
            """,
            
            f"""{DOKTRIN_TPA}
            BAGIAN 2: Tulis 'BAB II. SPESIFIKASI MATERIAL BETON STRUKTURAL'.
            - Mengacu pada SNI 2847:2019, uraikan syarat ketat untuk Semen Portland, Agregat Kasar/Halus, dan Air kerja.
            - Uraikan syarat penggunaan Bahan Tambah (Admixture) yang bebas klorida.
            - Jelaskan aturan Mix Design (Rancangan Campuran) dan batasan nilai Slump Beton agar tidak terjadi keropos (honeycomb).
            """,
            
            f"""{DOKTRIN_TPA}
            BAGIAN 3: Tulis 'BAB III. PELAKSANAAN PENGECORAN & PERAWATAN BETON'.
            - Uraikan prosedur persiapan sebelum pengecoran (pembersihan bekisting, penyiraman).
            - Aturan batas waktu beton segar (Ready Mix) sejak keluar dari batching plant.
            - Metode pemadatan beton menggunakan vibrator mekanis (jarak jarum, lama getaran).
            - Prosedur perawatan beton (Curing) selama 7 hari pertama pasca-pengecoran sesuai SNI.
            """,
            
            f"""{DOKTRIN_TPA}
            BAGIAN 4: Tulis 'BAB IV. PEKERJAAN PEMBESIAN & BEKISTING (FORMWORK)'.
            - Uraikan syarat toleransi pemotongan dan pembengkokan baja tulangan ulir/polos.
            - Aturan penyambungan lewatan tulangan (Lap Splice) dan penggunaan kawat bendrat sesuai SNI 2847:2019 Bab 25.
            - Syarat material bekisting (Plywood film face) dan toleransi lendutan maksimal bekisting saat dicor.
            """,
            
            f"""{DOKTRIN_TPA}
            BAGIAN 5: Tulis 'BAB V. PEKERJAAN BAJA STRUKTURAL & PENGELASAN'.
            - Uraikan spesifikasi material profil baja (misal BJ-41/BJ-37).
            - Syarat penggunaan baut mutu tinggi (High Tension Bolt - HTB) dan metode pengencangannya.
            - Syarat kualifikasi juru las (Welder bersertifikat) dan metode pengelasan (SMAW/FCAW) mengacu standar AWS D1.1 dan SNI 1729:2020.
            """,
            
            f"""{DOKTRIN_TPA}
            BAGIAN 6: Tulis 'BAB VI. PENGENDALIAN MUTU (QUALITY CONTROL) & PENGUJIAN'.
            - Uraikan prosedur pengambilan sampel benda uji silinder beton (jumlah sampel per volume pengecoran) dan umur uji (7, 14, 28 hari).
            - Kewajiban uji tarik baja tulangan berkala sesuai SNI 2052:2017.
            - Kewajiban uji tak merusak (Non-Destructive Test / NDT) seperti Ultrasonic Flaw Detector (UT) untuk sambungan las kritis.
            """
        ]

    else:
        return [f"{DOKTRIN_TPA}\nPROYEK: {project_name}\nTUGAS: Buat Pendahuluan dan Kriteria Desain."]
