import sys
import os
import math

# ==============================================================================
# KONFIGURASI PENGUJIAN (AUDIT COMPLIANCE)
# ==============================================================================
print("🚀 MEMULAI PROSES AUDIT OTOMATIS SMARTBIM ENGINEEX...")
print("📂 Memuat modul engineering...")

# Trik Import agar bisa membaca file di dalam folder modules maupun root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # 1. Coba Import Library Utama (Jantung Aplikasi)
    from modules.struktur import libs_gempa as quake
    from modules.struktur import libs_sni as sni
    
    # 2. Coba Import Tools (Jembatan Aplikasi)
    # Kita cek apakah ada di root atau di modules
    try:
        import libs_tools as tools
    except ImportError:
        try:
            from modules.utils import libs_tools as tools
        except ImportError:
            print("⚠️ Warning: libs_tools tidak ditemukan, pengujian fokus ke Core Engine.")
            tools = None

    print("✅ BERHASIL MEMUAT LIBRARY. SIAP UJI VALIDASI.")

except ImportError as e:
    print(f"❌ ERROR KRITIS: Gagal memuat library. Pastikan struktur folder benar.\nDetail: {e}")
    sys.exit()

# ==============================================================================
# FUNGSI PENGUJIAN (GOLDEN DATASET)
# ==============================================================================

def run_golden_dataset_test():
    score = 0
    total_test = 0
    
    print("\n" + "="*60)
    print("   PROTOKOL VERIFIKASI KEPATUHAN SNI (GOLDEN DATASET)   ")
    print("="*60)

    # ------------------------------------------------------------------
    # TEST CASE 1: INTERPOLASI GEMPA (SNI 1726:2019)
    # Ref: Laporan Audit Bagian 3.2.2 (Skenario Uji A)
    # Input: Tanah Sedang (SD), Ss = 0.60g
    # Target: Fa harus 1.32 (Interpolasi antara 1.4 dan 1.2)
    # ------------------------------------------------------------------
    print("\n🔹 UJI 1: INTERPOLASI SEISMIK (Koefisien Fa)")
    total_test += 1
    
    try:
        # Inisialisasi Engine Gempa
        engine = quake.SNI_Gempa_2019(Ss=0.60, S1=0.30, Kelas_Situs='SD')
        fa_hasil = engine.Fa
        fa_target = 1.32
        
        # Toleransi 0.001 (presisi 3 desimal)
        if abs(fa_hasil - fa_target) < 0.001:
            print(f"   [✅ LULUS] Input Ss=0.60 (SD) -> Output Fa={fa_hasil} (Sesuai Target {fa_target})")
            score += 1
        else:
            print(f"   [❌ GAGAL] Input Ss=0.60 (SD) -> Output Fa={fa_hasil}. Seharusnya {fa_target}.")
            print("   -> Cek logika interpolasi di libs_gempa.py!")
    except Exception as e:
        print(f"   [❌ ERROR] Terjadi crash saat uji gempa: {e}")

    # ------------------------------------------------------------------
    # TEST CASE 2: PENANGANAN BATAS ATAS (CLAMPING)
    # Ref: Laporan Audit Bagian 3.2.2 (Skenario Uji B)
    # Input: Tanah Sedang (SD), Ss = 1.60g (Di atas tabel maks 1.5)
    # Target: Fa harus tertahan di 1.0 (Tidak boleh ekstrapolasi turun)
    # ------------------------------------------------------------------
    print("\n🔹 UJI 2: STABILITAS NUMERIK (Batas Atas Tabel)")
    total_test += 1
    
    try:
        engine = quake.SNI_Gempa_2019(Ss=1.60, S1=0.50, Kelas_Situs='SD')
        fa_hasil = engine.Fa
        fa_target = 1.0
        
        if fa_hasil == fa_target:
            print(f"   [✅ LULUS] Input Ss=1.60 (SD) -> Output Fa={fa_hasil} (Clamping Aman)")
            score += 1
        else:
            print(f"   [❌ GAGAL] Input Ss=1.60 (SD) -> Output Fa={fa_hasil}. Seharusnya {fa_target}.")
            print("   -> Bahaya! Aplikasi melakukan ekstrapolasi ilegal.")
    except Exception as e:
        print(f"   [❌ ERROR] Crash saat uji clamping: {e}")

    # ------------------------------------------------------------------
    # TEST CASE 3: TANAH LUNAK & PERINGATAN (WARNING SYSTEM)
    # Ref: Laporan Audit Bagian 2.2.1 (Skenario Uji C - Modifikasi SE)
    # Input: Tanah Lunak (SE), S1 = 0.25g (S1 >= 0.2 wajib SSRA)
    # Target: Harus ada Note/Warning yang mengandung kata "CRITICAL" atau "Analisis"
    # ------------------------------------------------------------------
    print("\n🔹 UJI 3: KEPATUHAN REGULASI (Peringatan Tanah Lunak)")
    total_test += 1
    
    try:
        engine = quake.SNI_Gempa_2019(Ss=0.8, S1=0.25, Kelas_Situs='SE')
        note_hasil = str(engine.Note).upper()
        
        keyword1 = "CRITICAL"
        keyword2 = "ANALISIS"
        
        if keyword1 in note_hasil or keyword2 in note_hasil:
            print(f"   [✅ LULUS] Sistem mendeteksi bahaya S1>=0.2 pada SE.")
            print(f"   -> Pesan Sistem: '{engine.Note}'")
            score += 1
        else:
            print(f"   [❌ GAGAL] Tidak ada peringatan keras untuk S1=0.25 di Tanah Lunak.")
            print(f"   -> Pesan Aktual: '{engine.Note}'")
    except Exception as e:
        print(f"   [❌ ERROR] Crash saat uji warning: {e}")

    # ------------------------------------------------------------------
    # TEST CASE 4: SIZE EFFECT BETON (SNI 2847:2019)
    # Ref: Laporan Audit Bagian 4.2 (Efek Ukuran)
    # Input: Balok Tebal d=1000mm, TANPA Sengkang (Av=0)
    # Target: Lambda_s = sqrt(2 / (1 + 1000/254)) = 0.6366
    # ------------------------------------------------------------------
    print("\n🔹 UJI 4: SIZE EFFECT BETON (Balok Transfer/Pilecap)")
    total_test += 1
    
    try:
        # Mutu fc 30 MPa, fy 400 MPa
        engine_beton = sni.SNI_Concrete_2019(fc=30, fy=400)
        
        # Parameter: bw=1000, d=1000, Av=0, As=3000 (Rho normal)
        # PENTING: As_longitudinal harus diisi agar rumus detail aktif
        vc, lambda_s, trace = engine_beton.hitung_geser_beton_vc(
            bw=1000, d=1000, Av_terpasang=0, Nu=0, Ag=1000000, As_longitudinal=5000
        )
        
        # Hitung target manual presisi
        target_lambda = math.sqrt(2.0 / (1.0 + (1000 / 254.0)))
        
        if abs(lambda_s - target_lambda) < 0.001:
            print(f"   [✅ LULUS] Input d=1000mm (No Sengkang) -> Lambda_s={lambda_s:.4f}")
            print(f"   -> Target SNI: {target_lambda:.4f}")
            score += 1
        else:
            print(f"   [❌ GAGAL] Perhitungan Lambda_s salah. Dapat {lambda_s}, Seharusnya {target_lambda:.4f}")
            print("   -> Cek konstanta pembagi di libs_sni.py (Harus 254.0, bukan 250!)")
    except Exception as e:
        print(f"   [❌ ERROR] Crash saat uji beton: {e}")

    # ------------------------------------------------------------------
    # TEST CASE 5: LOGIKA SENGKANG (BYPASS SIZE EFFECT)
    # Ref: Laporan Audit Bagian 4.3 (Kondisional)
    # Input: Balok Tebal d=1000mm, DENGAN Sengkang (Av > 0)
    # Target: Lambda_s harus 1.0 (Efek ukuran dimatikan)
    # ------------------------------------------------------------------
    print("\n🔹 UJI 5: LOGIKA KONDISIONAL (Balok Bersengkang)")
    total_test += 1
    
    try:
        engine_beton = sni.SNI_Concrete_2019(fc=30, fy=400)
        # Av_terpasang = 157 (Ada sengkang)
        vc, lambda_s, trace = engine_beton.hitung_geser_beton_vc(
            bw=1000, d=1000, Av_terpasang=157, Nu=0, Ag=1000000, As_longitudinal=5000
        )
        
        if lambda_s == 1.0:
            print(f"   [✅ LULUS] Balok d=1000mm (Ada Sengkang) -> Lambda_s={lambda_s}")
            print("   -> Logika pengabaian Size Effect berfungsi benar.")
            score += 1
        else:
            print(f"   [❌ GAGAL] Lambda_s tetap dihitung ({lambda_s}) padahal ada sengkang!")
            print("   -> Pemborosan biaya (Over-conservative). Cek logika if-else di libs_sni.py")
    except Exception as e:
        print(f"   [❌ ERROR] Crash saat uji sengkang: {e}")

    # ==============================================================================
    # LAPORAN AKHIR
    # ==============================================================================
    print("\n" + "="*60)
    print(f"HASIL AKHIR AUDIT: {score} DARI {total_test} SKENARIO LULUS")
    print("="*60)
    
    if score == total_test:
        print("""
⭐⭐⭐⭐⭐ STATUS: CERTIFIED SNI COMPLIANT ⭐⭐⭐⭐⭐
Selamat! Aplikasi SmartBIMEngineex telah lulus uji verifikasi teknis.
- Algoritma Gempa: VALID (Interpolasi Linear)
- Algoritma Beton: VALID (Size Effect + Presisi Metrik)
- Stabilitas: AMAN

Anda sekarang dapat menyertakan hasil output skrip ini sebagai
lampiran 'Laporan Validasi Perangkat Lunak' untuk sidang TABG.
""")
    else:
        print("""
⚠️ STATUS: PERLU PERBAIKAN (NON-COMPLIANT)
Masih ada kegagalan pada uji kritis. 
Mohon perbaiki file library sesuai pesan error di atas sebelum rilis.
""")

if __name__ == "__main__":
    run_golden_dataset_test()
