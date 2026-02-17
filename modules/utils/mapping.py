# File: modules/utils/mapping.py

IFC_MAPPING = {
    "IfcWall": "Dinding",
    "IfcWallStandardCase": "Dinding Standar",
    "IfcSlab": "Pelat Lantai",
    "IfcBeam": "Balok",
    "IfcColumn": "Kolom",
    "IfcWindow": "Jendela",
    "IfcDoor": "Pintu",
    "IfcCovering": "Finishing/Lantai",
    "IfcFooting": "Pondasi",
    "IfcPile": "Tiang Pancang",
    "IfcMember": "Komponen Struktur",
    "IfcStair": "Tangga"
}

def get_indonesian_name(ifc_class):
    return IFC_MAPPING.get(ifc_class, ifc_class)
