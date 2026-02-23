import os
import sys

# ==============================================================================
# 1. SETUP ENVIRONMENT QGIS (HEADLESS MODE)
# ==============================================================================
QGIS_ROOT = r"C:\Program Files\QGIS 3.40.14"

# Suntikkan path agar tidak error DLL C++
os.environ['PATH'] = f"{QGIS_ROOT}\\bin;{QGIS_ROOT}\\apps\\qgis\\bin;{os.environ['PATH']}"
os.environ['PROJ_LIB'] = f"{QGIS_ROOT}\\share\\proj"
os.environ['GDAL_DATA'] = f"{QGIS_ROOT}\\share\\gdal"

# Tambahkan path Python QGIS
qgis_python_path = f"{QGIS_ROOT}\\apps\\qgis\\python"
if qgis_python_path not in sys.path:
    sys.path.insert(0, qgis_python_path)
    sys.path.insert(0, f"{qgis_python_path}\\plugins")

# ==============================================================================
# 2. INISIALISASI MESIN QGIS
# ==============================================================================
try:
    from qgis.core import QgsApplication, QgsVectorLayer, QgsDistanceArea
    
    # False = Tanpa Antarmuka Grafis (Headless)
    QgsApplication.setPrefixPath(f"{QGIS_ROOT}\\apps\\qgis", True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    MESIN_QGIS_SIAP = True
except Exception as e:
    MESIN_QGIS_SIAP = False
    pesan_error = str(e)

# ==============================================================================
# 3. CLASS ENGINE GIS
# ==============================================================================
class GIS_Engine:
    def __init__(self):
        self.engine_ready = MESIN_QGIS_SIAP

    def analisis_luas_geojson(self, file_path):
        """
        Membaca file GeoJSON/KML dan menghitung luas area total dalam METER PERSEGI.
        """
        if not self.engine_ready:
            return {"error": f"❌ QGIS Engine gagal dimuat: {pesan_error}"}

        # Mesin QGIS membaca file vektor
        layer = QgsVectorLayer(file_path, "Area_Proyek", "ogr")
        
        if not layer.isValid():
            return {"error": "❌ File spasial tidak valid atau format tidak didukung."}

        # --- FIX BUG: ALAT UKUR AREA (METER PERSEGI) ---
        # Membuat alat ukur jarak/area dengan mempertimbangkan kelengkungan bumi
        ukur_area = QgsDistanceArea()
        ukur_area.setEllipsoid('WGS84') # Standar GPS/Google Earth
        ukur_area.setSourceCrs(layer.crs(), layer.transformContext())

        total_luas_m2 = 0.0
        
        # Iterasi setiap poligon dan hitung luas fisiknya
        for feature in layer.getFeatures():
            geom = feature.geometry()
            # Hitung menggunakan alat ukur ellipsoid agar satuannya meter persegi
            luas_poligon = ukur_area.measureArea(geom) 
            total_luas_m2 += luas_poligon

        return {
            "Total_Luas_m2": round(total_luas_m2, 2),
            "Total_Luas_Ha": round(total_luas_m2 / 10000, 2),
            "Status": "✅ Dihitung presisi dengan QgsDistanceArea (Elipsoid WGS84)"
        }

    def shutdown(self):
        """
        Fungsi untuk mematikan mesin.
        Catatan: Jangan dipanggil di Streamlit agar mesin tetap standby.
        Hanya gunakan jika menjalankan skrip ini secara stand-alone (via terminal).
        """
        if self.engine_ready:
            qgs.exitQgis()
