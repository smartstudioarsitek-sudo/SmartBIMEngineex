# ==============================================================================
# 📄 NAMA FILE: test_qgis.py
# 📍 LOKASI: Folder Root (Sejajar dengan app_enginex.py)
# ==============================================================================
import os
import json

print("⏳ [1/4] Memuat pustaka dari modules.utils.libs_gis...")
try:
    from modules.utils.libs_gis import GIS_Engine
    print("✅ [1/4] Pustaka berhasil diimpor!")
except Exception as e:
    print(f"❌ [1/4] GAGAL mengimpor pustaka: {e}")
    exit()

print("⏳ [2/4] Membuat file GeoJSON dummy (persegi sederhana) untuk testing...")
# Membuat file GeoJSON sementara berukuran kotak sederhana
dummy_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"Nama": "Area Test"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[105.25, -5.40], [105.26, -5.40], [105.26, -5.41], [105.25, -5.41], [105.25, -5.40]]]
            }
        }
    ]
}

dummy_path = "test_area.geojson"
with open(dummy_path, "w") as f:
    json.dump(dummy_geojson, f)
print(f"✅ [2/4] File {dummy_path} berhasil dibuat.")

print("⏳ [3/4] Menghidupkan Mesin QGIS Headless...")
engine = GIS_Engine()

if engine.engine_ready:
    print("✅ [3/4] Mesin QGIS 3.40.14 BERHASIL HIDUP di latar belakang!")
    
    print("⏳ [4/4] Mencoba membaca dan menghitung luas dari GeoJSON...")
    hasil = engine.analisis_luas_geojson(dummy_path)
    
    print("\n" + "="*50)
    print("🎉 HASIL ANALISIS SPASIAL:")
    for key, value in hasil.items():
        print(f"   - {key}: {value}")
    print("="*50 + "\n")
    
    # Matikan mesin
    engine.shutdown()
    print("✅ Testing Selesai. Mesin QGIS dimatikan dengan aman.")
else:
    print("❌ [3/4] GAGAL: Mesin QGIS tidak bisa hidup. Periksa kembali path instalasi di libs_gis.py")

# Hapus file dummy agar rapi
if os.path.exists(dummy_path):
    os.remove(dummy_path)
