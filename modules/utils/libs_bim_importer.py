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
            verts = shape.geometry.verts
            faces = shape.geometry.faces
            
            # Hitung volume presisi dari Mesh Polyhedron (bukan Bounding Box)
            # Menggunakan Teorema Divergensi untuk menghitung volume dari titik koordinat
            def calc_mesh_volume(v, f):
                vol = 0.0
                for i in range(0, len(f), 3):
                    # Ambil 3 titik sudut segitiga
                    p1 = np.array(v[f[i]*3 : f[i]*3+3])
                    p2 = np.array(v[f[i+1]*3 : f[i+1]*3+3])
                    p3 = np.array(v[f[i+2]*3 : f[i+2]*3+3])
                    # Determinan / 6 (Volume Tetrahedron)
                    vol += np.dot(p1, np.cross(p2, p3)) / 6.0
                return abs(vol)

            return calc_mesh_volume(verts, faces)
        except:
            return 0.0
        
    def get_analytical_nodes(self, element):
        """
        Mengekstrak Titik Simpul (Nodes) untuk Analisis Struktur FEM.
        Mengubah elemen 3D (Kolom/Balok) menjadi Garis As (Centerline).
        """
        try:
            # 1. Ambil Titik Awal (Origin Node) dari Local Placement
            placement = element.ObjectPlacement
            relative_placement = placement.RelativePlacement
            
            # Ekstrak koordinat X, Y, Z titik bawah/awal
            location = relative_placement.Location.Coordinates
            node_start = np.array(location)
            
            # 2. Ambil Titik Akhir (End Node) berdasarkan arah Extrusion
            # Sebagian besar struktur di IFC dimodelkan menggunakan IfcExtrudedAreaSolid
            representation = element.Representation
            for rep in representation.Representations:
                for item in rep.Items:
                    if item.is_a('IfcExtrudedAreaSolid'):
                        # Ambil vektor arah (biasanya Z untuk kolom, X/Y untuk balok)
                        direction = np.array(item.ExtrudedDirection.DirectionRatios)
                        depth = item.Depth
                        
                        # Hitung Node Akhir: Posisi Awal + (Vektor Arah * Panjang)
                        node_end = node_start + (direction * depth)
                        
                        return {
                            "Node_Start": tuple(np.round(node_start, 6)),
                            "Node_End": tuple(np.round(node_end, 6)),
                            "Length": round(depth, 3)
                        }
                        
            return None
        except Exception as e:
            return None
    # ... (sisanya sama)

