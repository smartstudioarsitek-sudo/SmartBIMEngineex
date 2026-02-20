# modules/utils/prompt_registry.py

# ==============================================================================
# DOKTRIN KETAT UNTUK AI (MEMAKSA FORMAT DED & SITASI SNI)
# ==============================================================================
DOKTRIN_TPA = """
[INSTRUKSI MUTLAK & WAJIB DIPATUHI]:
1. BERHENTI bertingkah seperti AI/Chatbot. JANGAN ADA kalimat pembuka/penutup seperti "Tentu, berikut adalah laporannya", "Semoga membantu", atau "Jika ada pertanyaan".
2. LANGSUNG cetak isi dokumen sesuai format laporan Detail Engineering Design (DED) yang kaku, baku, dan profesional (EYD).
3. SETIAP menyebutkan parameter atau metode, WAJIB sertakan kutipan nomor Pasal atau Tabel dari SNI yang relevan (Contoh: "Berdasarkan SNI 1726:2019 Pasal 7.9.1.1..." atau "Mengacu pada SNI 2847:2019 Pasal 18.7...").
4. Format perhitungan HARUS seperti 'Hand-Calculation' atau White-Box. Tampilkan rumus, angka masukan, dan hasil akhirnya.
"""

def get_chain_prompts(category, project_name, data_context=""):
    """
    Mengembalikan skenario prompt berdasarkan Kategori Keahlian (Persona).
    Didesain dengan metode 6-Step Chaining agar AI menghasilkan laporan super detail tanpa terpotong.
    """
    
    # === 1. MODUL STRUKTUR (SNI 1726, 1727, 2847) ===
    if category == "STRUKTUR":
        return [
            f"""{DOKTRIN_TPA}
            PROYEK: {project_name} | KONTEKS: {data_context}
            TUGAS BAGIAN 1: Tulis 'BAB I. PENDAHULUAN & KRITERIA DESAIN STRUKTUR'.
            - Jelaskan deskripsi proyek dan filosofi desain struktur.
            - Buat sub-bab Standar Rujukan yang memuat list SNI wajib (SNI 1726:2019, SNI 1727:2020, SNI 2847:2019).
            - Buat sub-bab Properti Material (Mutu Beton fc', Mutu Baja Tulangan fy) beserta batasan modulus elastisitasnya sesuai SNI.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 2: Tulis 'BAB II. ANALISIS PEMBEBANAN GRAVITASI & ANGIN'.
            - Buat rincian Beban Mati (Berat sendiri, partisi, ME) dan Beban Hidup (Fungsi ruang) berdasarkan SNI 1727:2020.
            - Berikan contoh tabel kombinasi pembebanan ultimate (LRFD) dan Layan (ASD).
            - Sertakan penjelasan singkat mengenai asumsi beban angin.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 3: Tulis 'BAB III. ANALISIS KINERJA SEISMIK & RESPON SPEKTRUM'.
            - Mengacu pada SNI 1726:2019, jelaskan parameter Ss, S1, Fa, Fv, SDS, SD1 berdasarkan asumsi kelas situs tanah dari konteks proyek.
            - Jelaskan prosedur pembentukan Kurva Respons Spektrum Desain.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 4: Tulis 'BAB IV. EVALUASI PARAMETER DINAMIS STRUKTUR'.
            - Buat tabel simulasi/penjelasan pengecekan Partisipasi Massa Ragam (Wajib $\ge 90\%$) sesuai SNI 1726:2019 Psl 7.9.1.1.
            - Buat simulasi pengecekan Penskalaan Gaya Geser Dasar ($V_{{dinamik}} \ge 100\% V_{{statik}}$) sesuai Psl 7.9.4.1.
            - Jelaskan prosedur kontrol Story Drift (Simpangan Antar Lantai) dan Efek P-Delta.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 5: Tulis 'BAB V. DESAIN KAPASITAS PENAMPANG BETON BERTULANG'.
            - Mengacu SNI 2847:2019 (SRPMK), jelaskan kontrol 'Strong Column - Weak Beam' ($\sum M_{{nc}} \ge 1.2 \sum M_{{nb}}$).
            - Jelaskan prosedur Desain Geser Kapasitas berdasarkan Probable Moment ($M_{{pr}}$) dengan asumsi tegangan baja $1.25 f_y$.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 6: Tulis 'BAB VI. KESIMPULAN & REKOMENDASI AUDIT TPA'.
            - Berikan kesimpulan final bahwa struktur aman dan mematuhi seluruh kaidah SNI.
            - Buat format kolom Lembar Pengesahan di bagian paling bawah untuk ditandatangani oleh Perencana dan Penilai Teknis.
            """
        ]

    # === 2. MODUL SUMBER DAYA AIR (SNI 2415 & KP-01) ===
    elif category == "WATER":
        return [
            f"""{DOKTRIN_TPA}
            PROYEK: {project_name} | KONTEKS: {data_context}
            TUGAS BAGIAN 1: Tulis 'BAB I. PENDAHULUAN & KARAKTERISTIK DAS'.
            - Jelaskan ruang lingkup proyek SDA ini.
            - Deskripsikan parameter Daerah Aliran Sungai (Luas A, Panjang Sungai L).
            - Sebutkan rujukan wajib: SNI 2415:2016 (Banjir) dan KP-01 (Irigasi).
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 2: Tulis 'BAB II. ANALISIS STATISTIK CURAH HUJAN EKSTREM'.
            - Mengacu pada SNI 2415:2016, jelaskan penggunaan metode Log Pearson Tipe III sebagai standar utama PUPR.
            - Buat narasi perbandingan mengapa Log Pearson III lebih baik dari metode Gumbel untuk proyek ini.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 3: Tulis 'BAB III. PERHITUNGAN HUJAN EFEKTIF (NRCS-CN)'.
            - Jelaskan tata cara transformasi curah hujan total ($P$) menjadi hujan efektif ($P_e$).
            - Kaitkan pemilihan nilai Curve Number (CN) dengan kondisi tata guna lahan (Land Use) di lokasi proyek. Tampilkan rumus $S = (25400/CN) - 254$.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 4: Tulis 'BAB IV. PEMODELAN HIDROGRAF SATUAN SINTETIS (HSS) NAKAYASU'.
            - Uraikan parameter empiris Nakayasu: Waktu Kelambatan ($T_g$), Waktu Puncak ($T_p$), dan Debit Puncak ($Q_p$).
            - Berikan rumus dasarnya dan jelaskan fase lengkung naik (rising limb) dan turun (falling limb).
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 5: Tulis 'BAB V. ANALISIS KETERSEDIAAN AIR & HIDROLIKA'.
            - Jika proyek terkait ketersediaan air, singgung metode FJ Mock atau Penman.
            - Jika terkait JIAT (Jaringan Irigasi Air Tanah), jelaskan perhitungan Head Loss dengan persamaan Hazen-Williams dan Kurva Pompa.
            """,
            
            f"""{DOKTRIN_TPA}
            TUGAS BAGIAN 6: Tulis 'BAB VI. KESIMPULAN & REKOMENDASI MITIGASI BANJIR'.
            - Tarik kesimpulan angka Debit Puncak ($Q_p$) untuk periode ulang tertentu (misal 50 tahun).
            - Buat kolom Lembar Pengesahan laporan siap cetak.
            """
        ]

    # === DEFAULT FALLBACK UNTUK MODUL LAIN (COST, ARSITEK, GEOTEK) ===
    else:
        return [
            f"{DOKTRIN_TPA}\nPROYEK: {project_name}\nTUGAS 1: Buat Pendahuluan dan Kriteria Desain.",
            f"{DOKTRIN_TPA}\nTUGAS 2: Buat Analisis Teknis dan Rincian Metode.",
            f"{DOKTRIN_TPA}\nTUGAS 3: Buat Kesimpulan, Rekomendasi, dan Lembar Pengesahan."
        ]
