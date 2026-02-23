import os
import sys

# ==============================================================================
# 1. SETUP ENVIRONMENT QGIS (HEADLESS MODE)
# Menghubungkan Streamlit dengan mesin QGIS 3.40.14
# ==============================================================================
QGIS_ROOT = r"C:\Program Files\QGIS 3.40.14"

# Suntikkan folder 'bin' dan pengaturan spasial ke Windows PATH agar tidak error DLL
os.environ['PATH'] = f"{QGIS_ROOT}\\bin;{QGIS_ROOT}\\apps\\qgis\\bin;{os.environ['PATH']}"
os.environ['PROJ_LIB'] = f"{QGIS_ROOT}\\share\\proj"
os.environ['GDAL_DATA'] = f"{QGIS_ROOT}\\share\\gdal"

# Tambahkan path pustaka Python milik QGIS agar dikenali oleh VS Code
qgis_python_path = f"{QGIS_ROOT}\\apps\\qgis\\python"
if qgis_python_path not in sys.path:
    sys.path.insert(0, qgis_python_path)
    sys.path.insert(0, f"{qgis_python_path}\\plugins")

# ==============================================================================
# 2. INISIALISASI MESIN QGIS
# ==============================================================================
try:
    from qgis.core import QgsApplication, QgsVectorLayer
    
    # False = Tanpa Antarmuka Grafis (Headless)
    QgsApplication.setPrefixPath(f"{QGIS_ROOT}\\apps\\qgis", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    MESIN_QGIS_SIAP = True
except Exception as e:
    MESIN_QGIS_SIAP = False
    pesan_error = str(e)

# ==============================================================================
# 3. CLASS ENGINE GIS (UNTUK DIPANGGIL DI APP_ENGINEX.PY)
# ==============================================================================
class GIS_Engine:
    def __init__(self):
        self.engine_ready = MESIN_QGIS_SIAP

    def analisis_luas_geojson(self, file_path):
        """
        Membaca file GeoJSON/KML dan menghitung luas area total.
        Sangat berguna untuk otomatisasi RAB Pembersihan Lahan.
        """
        if not self.engine_ready:
            return {"error": f"❌ QGIS Engine gagal dimuat: {pesan_error}"}

        # Mesin QGIS membaca file vektor
        layer = QgsVectorLayer(file_path, "Area_Proyek", "ogr")
        
        if not layer.isValid():
            return {"error": "❌ File spasial tidak valid atau format tidak didukung."}

        total_luas_m2 = 0.0
        
        # Iterasi setiap poligon di dalam file dan hitung luasnya
        for feature in layer.getFeatures():
            geom = feature.geometry()
            total_luas_m2 += geom.area()

        return {
            "Total_Luas_m2": round(total_luas_m2, 2),
            "Total_Luas_Ha": round(total_luas_m2 / 10000, 2),
            "Status": "✅ Dihitung dengan PyQGIS 3.40.14"
        }

    def shutdown(self):
        """PENTING: Matikan mesin QGIS agar memori RAM terbebas setelah dipakai."""
        if self.engine_ready:
            qgs.exitQgis()
