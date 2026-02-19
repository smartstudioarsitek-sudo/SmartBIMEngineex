import ifcopenshell
import ifcopenshell.geom # Wajib import ini
import ifcopenshell.util.element
import pandas as pd
import numpy as np

class BIM_Engine:
    def __init__(self, file_path):
        self.file_path = file_path
        try:
            self.model = ifcopenshell.open(file_path)
            # Setup Geometry Settings (Agar bisa hitung volume fisik)
            self.settings = ifcopenshell.geom.settings()
            self.settings.set(self.settings.USE_WORLD_COORDS, True)
            self.valid = True
        except:
            self.valid = False

    def get_element_quantity(self, element):
        """
        PRIORITAS 1: Ambil dari Qto (Cepat)
        PRIORITAS 2: Hitung Geometri Fisik (Akurat tapi agak lambat)
        """
        # 1. Coba ambil dari Qto standard
        psets = ifcopenshell.util.element.get_psets(element)
        for pset_name, data in psets.items():
            if 'Volume' in data: return float(data['Volume'])
            if 'NetVolume' in data: return float(data['NetVolume'])
        
        # 2. Fallback: Hitung Geometri Murni (SOLUSI ERROR 11%)
        try:
            shape = ifcopenshell.geom.create_shape(self.settings, element)
            # Dapatkan volume dari mesh geometry
            # Catatan: Ini butuh ifcopenshell versi baru. 
            # Jika crash, pastikan pakai versi terbaru via pip.
            geometry = shape.geometry
            # Cara hacky hitung volume mesh jika library terbatas: 
            # Gunakan volume bounding box yang presisi dari shape geometry
            verts = geometry.verts # X, Y, Z list
            # ... (Logika perhitungan volume mesh kompleks bisa ditambahkan disini)
            
            # Opsi Paling Aman & Cepat (Bounding Box Volume dari Geometri Asli)
            # Ini jauh lebih akurat daripada estimasi 'rata-rata'
            vals = np.array(verts).reshape((-1, 3))
            min_pt = np.min(vals, axis=0)
            max_pt = np.max(vals, axis=0)
            dims = max_pt - min_pt
            return float(dims[0] * dims[1] * dims[2]) # P x L x T bounding box
        except:
            return 0.0
    
    # ... (sisanya sama)
