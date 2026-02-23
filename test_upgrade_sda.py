import pandas as pd
import numpy as np
import pprint

# Pastikan Anda mengimpor class dari path yang benar sesuai struktur folder Anda
# Jika file ini ada di root, import-nya kira-kira seperti ini:
from modules.water.libs_bendung import Bendung_Engine
from modules.water.libs_irigasi import Irrigation_Engine
from modules.water.libs_jiat import JIAT_Engine
from modules.geotek.libs_topografi import Topografi_Engine

def run_audit_test():
    print("="*60)
    print("🚀 MEMULAI PENGUJIAN UPGRADE MODUL SDA (KP-01 s/d KP-07)")
    print("="*60)

    # ---------------------------------------------------------
    # TEST 1: MODUL BENDUNG (Analisis Rembesan Lane & Kantong Lumpur)
    # ---------------------------------------------------------
    print("\n[1/4] MENGUJI MODUL BENDUNG (libs_bendung.py) ...")
    bendung = Bendung_Engine()
    
    # Skenario 1A: Uji Piping (Metode Lane)
    # Asumsi Beda Tinggi Air (H) = 4.5m, Sheetpile 3m dan 2m, Lantai muka 15m. Tanah: Pasir Sedang
    hasil_lane = bendung.cek_rembesan_lane(
        delta_H=4.5, 
        list_Lv=[3.0, 2.0], # Kedalaman cut-off / sheetpile
        list_Lh=[10.0, 5.0], # Panjang lantai muka dan kolam olak
        jenis_tanah="pasir sedang"
    )
    print("  -> Hasil Analisis Piping (Metode Lane):")
    pprint.pprint(hasil_lane, indent=4)

    # Skenario 1B: Uji Kantong Lumpur
    # Debit 15 m3/s, kecepatan jatuh partikel pasir halus 0.04 m/s
    hasil_lumpur = bendung.dimensi_kantong_lumpur(Q_desain=15.0, kecepatan_endap_w=0.04, kecepatan_aliran_v=0.3)
    print("\n  -> Hasil Desain Kantong Lumpur:")
    pprint.pprint(hasil_lumpur, indent=4)


    # ---------------------------------------------------------
    # TEST 2: MODUL IRIGASI (Kebutuhan Air Tanaman NFR/IR)
    # ---------------------------------------------------------
    print("\n[2/4] MENGUJI MODUL IRIGASI (libs_irigasi.py) ...")
    irigasi = Irrigation_Engine()
    
    # Skenario: ETo = 5.2 mm/hari, Padi fase pertumbuhan (Kc=1.05), Hujan efektif 1.5 mm/hari
    hasil_nfr = irigasi.hitung_kebutuhan_air_irigasi(
        eto=5.2, kc=1.05, curah_hujan_efektif=1.5, perkolasi=2.0, wlr=1.0
    )
    print("  -> Hasil Perhitungan NFR & IR:")
    pprint.pprint(hasil_nfr, indent=4)


    # ---------------------------------------------------------
    # TEST 3: MODUL JIAT (Pompa Air Tenaga Surya / PATS)
    # ---------------------------------------------------------
    print("\n[3/4] MENGUJI MODUL JIAT (libs_jiat.py) ...")
    jiat = JIAT_Engine()
    
    # Skenario: Kebutuhan daya pompa dari hitungan sebelumnya adalah 5.5 kW. 
    # Lokasi NTB dengan Peak Sun Hours (PSH) 5.0 jam.
    hasil_pats = jiat.rancang_pats(power_pompa_kw=5.5, jam_operasi_harian=6, psh_lokasi=5.0, kapasitas_panel_wp=550)
    print("  -> Hasil Sizing Panel Surya (PATS):")
    pprint.pprint(hasil_pats, indent=4)


    # ---------------------------------------------------------
    # TEST 4: MODUL TOPOGRAFI (Simulasi Genangan Banjir 3D)
    # ---------------------------------------------------------
    print("\n[4/4] MENGUJI MODUL TOPOGRAFI (libs_topografi.py) ...")
    topo = Topografi_Engine()
    
    # Buat Dummy Data Topografi Lahan (Grid 100x100 meter, elevasi acak 10-20m)
    np.random.seed(42)
    df_dummy = pd.DataFrame({
        'X': np.random.uniform(0, 100, 200),
        'Y': np.random.uniform(0, 100, 200),
        'Z': np.random.uniform(10, 20, 200) 
    })
    
    # Skenario Banjir: Muka air naik hingga elevasi +16.5 meter
    fig_3d, hasil_banjir = topo.simulasi_genangan_banjir_3d(df_points=df_dummy, elevasi_banjir=16.5)
    
    print("  -> Hasil Kalkulasi Bathtub Inundation Model:")
    pprint.pprint(hasil_banjir, indent=4)
    if fig_3d:
        print("  ✅ Grafik 3D Plotly berhasil di-generate! (Gunakan Streamlit untuk merender grafik ini)")
    else:
        print("  ❌ Gagal membuat grafik 3D.")

    print("\n" + "="*60)
    print("🎉 SEMUA PENGUJIAN SELESAI DENGAN SUKSES!")
    print("="*60)

if __name__ == "__main__":
    run_audit_test()
