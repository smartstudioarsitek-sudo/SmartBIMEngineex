# ==============================================================================
# 📄 NAMA FILE: libs_gis.py
# 📍 LOKASI: modules/utils/libs_gis.py
# 🛠️ FUNGSI: Mesin Spasial Mandiri berbasis GeoPandas (Pengganti QGIS Desktop)
# ==============================================================================

import geopandas as gpd
import fiona

# Mengaktifkan dukungan untuk membaca file KML dan KMZ di Fiona/GeoPandas
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

class GIS_Engine:
    def __init__(self):
        # Karena kita pakai GeoPandas, mesin selalu siap tanpa perlu inisialisasi berat
        self.engine_ready = True

    def analisis_luas_geojson(self, file_path):
        """
        Membaca file GeoJSON, KML, atau KMZ dan menghitung luas area total.
        Otomatis mengubah proyeksi ke sistem Metrik (Meter Persegi).
        """
        try:
            # 1. Baca file spasial (otomatis mendeteksi GeoJSON / KML)
            gdf = gpd.read_file(file_path)
            
            # 2. Cek apakah file kosong
            if gdf.empty:
                return {"error": "❌ File spasial kosong atau tidak berisi poligon lahan."}

            # 3. Konversi Proyeksi (SANGAT PENTING)
            # File dari Google Earth biasanya bersatuan Derajat (EPSG:4326).
            # Kita konversi ke Web Mercator (EPSG:3857) agar satuannya menjadi Meter.
            gdf_metric = gdf.to_crs(epsg=3857)

            # 4. Hitung Total Luas (Meter Persegi)
            total_luas_m2 = gdf_metric.geometry.area.sum()

            return {
                "Total_Luas_m2": round(total_luas_m2, 2),
                "Total_Luas_Ha": round(total_luas_m2 / 10000, 2),
                "Status": "✅ Dihitung presisi dengan GeoPandas (Metric Projection)"
            }
            
        except Exception as e:
            return {"error": f"❌ Gagal memproses file spasial: {str(e)}"}

    def shutdown(self):
        """Fungsi dummy agar kompatibel dengan pemanggilan di libs_loader.py"""
        pass
