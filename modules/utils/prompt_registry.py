# modules/utils/prompt_registry.py

# ==============================================================================
# DOKTRIN KETAT UNTUK AI (MEMAKSA FORMAT DED & ANTI-LATEX)
# ==============================================================================
DOKTRIN_TPA = """
[INSTRUKSI MUTLAK & WAJIB DIPATUHI - FORMATTING]:
1. BERHENTI bertingkah seperti AI/Chatbot. JANGAN ADA kalimat pembuka/penutup. LANGSUNG cetak isi dokumen DED dengan bahasa Indonesia baku (EYD).
2. SETIAP menyebutkan parameter, WAJIB sertakan sitasi SNI (Contoh: "Berdasarkan SNI 1726:2019 Pasal 7...").
3. DILARANG KERAS MENGGUNAKAN SIMBOL LaTeX ($ atau $$) UNTUK RUMUS! Tulis rumus dengan plain-text biasa (Misal tulis: "Ec = 4700 x akar(fc)" BUKAN "$E_c = 4700 \\times \\sqrt{fc}$").
4. DILARANG MENGGUNAKAN TABEL MARKDOWN (|---|). Sajikan data dalam bentuk list (bullet/numbering) bertingkat yang rapi.
"""

def get_chain_prompts(category, project_name, data_context=""):
    """
    Mengembalikan skenario prompt berdasarkan Kategori Keahlian.
    Didesain dengan metode Chaining agar AI menghasilkan laporan tanpa terpotong.
    """
    if category == "STRUKTUR":
        return [
            f"""{DOKTRIN_TPA}
            PROYEK: {project_name} | KONTEKS: {data_context}
            BAGIAN 1: Tulis 'BAB I. PENDAHULUAN & KRITERIA DESAIN STRUKTUR'.
            - Jelaskan filosofi desain struktur tahan gempa.
            - Buat list Standar Rujukan (SNI 1726:2019, 1727:2020, 2847:2019).
            - Tuliskan Properti Material Beton dan Baja (gunakan plain text, misal fc = 30 MPa).
            """,
            f"""{DOKTRIN_TPA}
            BAGIAN 2: Tulis 'BAB II. ANALISIS PEMBEBANAN GRAVITASI & ANGIN'.
            - Rincikan Beban Mati dan Beban Hidup sesuai SNI 1727:2020.
            - Tuliskan kombinasi pembebanan ultimate (LRFD) dalam format list, jangan tabel!
            """,
            f"""{DOKTRIN_TPA}
            BAGIAN 3: Tulis 'BAB III. ANALISIS KINERJA SEISMIK'.
            - Jelaskan parameter Ss, S1, Fa, Fv, SDS, SD1 berdasarkan SNI 1726:2019. Tulis rumus dengan plain text.
            - Jelaskan syarat Kategori Desain Seismik (KDS) D dan Sistem SRPMK.
            """,
            f"""{DOKTRIN_TPA}
            BAGIAN 4: Tulis 'BAB IV. EVALUASI PARAMETER DINAMIS STRUKTUR'.
            - Jelaskan syarat Partisipasi Massa Ragam (Wajib >= 90%) sesuai SNI 1726:2019 Psl 7.9.1.1.
            - Jelaskan syarat Penskalaan Gaya Geser Dasar (V dinamik >= 100% V statik) sesuai Psl 7.9.4.1.
            """,
            f"""{DOKTRIN_TPA}
            BAGIAN 5: Tulis 'BAB V. DESAIN KAPASITAS PENAMPANG BETON BERTULANG'.
            - Jelaskan kontrol 'Strong Column - Weak Beam' (Rasio Mnc >= 1.2 Mnb) sesuai SNI 2847:2019.
            - Jelaskan prosedur Desain Geser Kapasitas (Mpr) dengan baja 1.25 fy.
            """,
            f"""{DOKTRIN_TPA}
            BAGIAN 6: Tulis 'BAB VI. KESIMPULAN AUDIT'.
            - Berikan kesimpulan akhir kelayakan struktur.
            - Jangan buat tabel tanda tangan, cukup buat list penandatangan (Perencana dan Penilai Teknis).
            """
        ]
    elif category == "WATER":
        return [
            f"""{DOKTRIN_TPA}\nPROYEK: {project_name}\nBAGIAN 1: Tulis 'BAB I. PENDAHULUAN & DAS' merujuk SNI 2415:2016.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 2: Tulis 'BAB II. ANALISIS HUJAN' jelaskan Log Pearson Tipe III.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 3: Tulis 'BAB III. HUJAN EFEKTIF' jelaskan metode NRCS Curve Number (CN).""",
            f"""{DOKTRIN_TPA}\nBAGIAN 4: Tulis 'BAB IV. HSS NAKAYASU' tuliskan parameter Tp, Tg, Qp dalam plain text.""",
            f"""{DOKTRIN_TPA}\nBAGIAN 5: Tulis 'BAB V. KESIMPULAN' dan rekomendasi debit banjir rencana."""
        ]
    else:
        return [f"{DOKTRIN_TPA}\nPROYEK: {project_name}\nTUGAS 1: Buat Pendahuluan dan Kriteria Desain."]
