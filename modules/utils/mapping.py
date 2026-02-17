# utils/mapping.py

IFC_TO_INDONESIA = {
    # Struktur Utama
    "IfcWall": "Dinding",
    "IfcWallStandardCase": "Dinding Standar",
    "IfcSlab": "Pelat Lantai",
    "IfcRoof": "Atap",
    "IfcBeam": "Balok Struktur",
    "IfcColumn": "Kolom Struktur",
    "IfcFooting": "Pondasi",
    "IfcPile": "Tiang Pancang",
    
    # Arsitektur & Bukaan
    "IfcWindow": "Jendela",
    "IfcDoor": "Pintu",
    "IfcStair": "Tangga",
    "IfcRailing": "Railing/Pagar",
    "IfcCovering": "Penutup/Finishing",
    
    # MEP (Mekanikal Elektrikal)
    "IfcFlowSegment": "Pipa/Ducting",
    "IfcFlowTerminal": "Terminal Air/Udara",
    "IfcDistributionElement": "Elemen Distribusi",
    
    # Furniture
    "IfcFurnishingElement": "Perabot",
}

def get_indonesian_name(ifc_class_name):
    """Menerjemahkan nama class IFC ke Bahasa Indonesia."""
    return IFC_TO_INDONESIA.get(ifc_class_name, ifc_class_name)
