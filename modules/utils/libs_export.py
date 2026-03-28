import pandas as pd
from io import BytesIO
import xlsxwriter
import sys
from thefuzz import process, fuzz # [PERBAIKAN TAHAP 2] Import Mesin NLP

class Export_Engine:
    def __init__(self):
        pass

    # =======================================================
    # FUNGSI 1: GENERATOR DXF (GAMBAR KERJA)
    # =======================================================
    def create_dxf(self, drawing_type, params):
        dxf = "0\nSECTION\n2\nENTITIES\n"
        def add_line(x1, y1, x2, y2, layer="STRUKTUR"):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
        def add_text(x, y, text, height=0.15, layer="TEXT"):
            return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{height}\n1\n{text}\n"
        
        if drawing_type == "BALOK":
            b = params.get('b', 300) / 1000
            h = params.get('h', 600) / 1000
            dxf += add_line(0, 0, b, 0) + add_line(b, 0, b, h) + add_line(b, h, 0, h) + add_line(0, h, 0, 0)
            dxf += add_text(b/2, -0.2, f"Lebar: {b*1000} mm")
            dxf += add_text(-0.3, h/2, f"Tinggi: {h*1000} mm")
            
        dxf += "0\nENDSEC\n0\nEOF\n"
        return dxf

    # =======================================================
    # FUNGSI 2: GENERATOR EXCEL RAB & AHSP (GOV.READY)
    # =======================================================
    def generate_7tab_rab_excel(self, data_boq, dict_database_ahsp, nama_proyek="Proyek_SmartBIM"):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # -------------------------------------------------------
        # FORMATTING EXCEL
        # -------------------------------------------------------
        fmt_title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter'})
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        fmt_border = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        fmt_currency = workbook.add_format({'border': 1, 'num_format': 'Rp #,##0.00', 'valign': 'vcenter'})
        fmt_number = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter'})
        fmt_bold_currency = workbook.add_format({'bold': True, 'border': 1, 'num_format': 'Rp #,##0.00', 'bg_color': '#FFFFE0', 'valign': 'vcenter'})
        
        # -------------------------------------------------------
        # INISIALISASI WORKSHEET
        # -------------------------------------------------------
        ws_rekap = workbook.add_worksheet('1. REKAPITULASI')
        ws_rab = workbook.add_worksheet('2. RAB')
        ws_ahsp = workbook.add_worksheet('4. AHSP S2 30 2025')
        ws_tkdn = workbook.add_worksheet('TKDN')
        
        # -------------------------------------------------------
        # SHEET 4: AHSP (MASTER DATABASE)
        # -------------------------------------------------------
        ws_ahsp.set_column('A:A', 5)
        ws_ahsp.set_column('B:B', 50)
        ws_ahsp.set_column('C:C', 10)
        ws_ahsp.set_column('D:D', 20)
        
        headers_ahsp = ['No', 'Uraian Pekerjaan / Komponen', 'Satuan', 'Harga Satuan (Rp)']
        for col, h in enumerate(headers_ahsp):
            ws_ahsp.write(0, col, h, fmt_header)
            
        map_baris_rekap = {} # Kamus penyimpan lokasi baris untuk ditarik ke RAB
        row_ahsp = 1
        no_ahsp = 1
        
        # Cetak isi AHSP
        for kunci_ahsp, data_item in dict_database_ahsp.items():
            # Baris Induk Pekerjaan
            ws_ahsp.write(row_ahsp, 0, no_ahsp, fmt_border)
            ws_ahsp.write(row_ahsp, 1, kunci_ahsp, fmt_border)
            ws_ahsp.write(row_ahsp, 2, data_item.get('Satuan', 'ls'), fmt_border)
            
            # Harga Satuan Utama (Diambil sebagai referensi formula)
            harga_total = data_item.get('Harga Satuan Pekerjaan', 0)
            ws_ahsp.write(row_ahsp, 3, harga_total, fmt_bold_currency)
            
            # Simpan baris ini ke kamus agar bisa dipanggil Excel
            map_baris_rekap[kunci_ahsp] = row_ahsp + 1 
            
            row_ahsp += 1
            no_ahsp += 1
            
        # -------------------------------------------------------
        # SHEET 2: RAB (BILL OF QUANTITIES)
        # -------------------------------------------------------
        ws_rab.set_column('A:A', 5)
        ws_rab.set_column('B:B', 40)
        ws_rab.set_column('C:C', 15)
        ws_rab.set_column('D:D', 15)
        ws_rab.set_column('E:E', 15)
        ws_rab.set_column('F:F', 20)
        ws_rab.set_column('G:G', 25)
        
        ws_rab.merge_range('A1:G1', f'RENCANA ANGGARAN BIAYA (RAB) - {nama_proyek}', fmt_title)
        
        headers_rab = ['No', 'Uraian Pekerjaan (Revit)', 'Kategori BIM', 'Volume', 'Satuan', 'Harga Satuan (Rp)', 'Jumlah Harga (Rp)']
        for col, h in enumerate(headers_rab):
            ws_rab.write(2, col, h, fmt_header)
            
        row_rab = 3
        no_rab = 1
        
        # [PERBAIKAN TAHAP 2] Siapkan daftar AHSP untuk Mesin NLP
        daftar_kunci_ahsp = list(map_baris_rekap.keys())
        
        for item in data_boq:
            nama_revit = str(item.get('Nama', 'Unknown'))
            kategori_revit = str(item.get('Kategori', 'Unknown'))
            
            # Toleransi untuk perbedaan kunci JSON ("Kuantitas" vs "Volume")
            volume_val = item.get('Kuantitas', item.get('Volume', 0.0))
            satuan_val = str(item.get('Satuan', 'Unit'))
            
            ws_rab.write(row_rab, 0, no_rab, fmt_border)
            ws_rab.write(row_rab, 1, nama_revit, fmt_border)
            ws_rab.write(row_rab, 2, kategori_revit, fmt_border)
            ws_rab.write(row_rab, 3, volume_val, fmt_number)
            ws_rab.write(row_rab, 4, satuan_val, fmt_border)
            
            # ===============================================================
            # [CORE ENGINE] FUZZY MATCHING NLP
            # ===============================================================
            matched = False
            nama_bersih = nama_revit.replace("Pekerjaan ", "").strip()
            
            if daftar_kunci_ahsp and volume_val > 0:
                # Cari probabilitas kemiripan tertinggi menggunakan algoritma Levenshtein
                best_match, score = process.extractOne(
                    nama_bersih, 
                    daftar_kunci_ahsp, 
                    scorer=fuzz.token_set_ratio
                )
                
                # Jika kemiripan di atas batas toleransi 80%, hubungkan rumusnya!
                if score >= 80:
                    baris_ditemukan = map_baris_rekap[best_match]
                    # Tulis rumus Excel yang melink ke Sheet AHSP
                    # Excel menggunakan kolom D (index 3) di sheet AHSP, jadi rumusnya ='4. AHSP S2 30 2025'!D{baris}
                    ws_rab.write_formula(row_rab, 5, f"='4. AHSP S2 30 2025'!D{baris_ditemukan}", fmt_currency)
                    matched = True
            
            # Jika NLP gagal mencocokkan, biarkan harga kosong (0) dan jangan gunakan harga Dummy
            if not matched:
                ws_rab.write(row_rab, 5, 0, fmt_currency)
                
            # Rumus Jumlah Harga = Volume (D) * Harga Satuan (F)
            baris_excel_rab = row_rab + 1
            ws_rab.write_formula(row_rab, 6, f"=D{baris_excel_rab}*F{baris_excel_rab}", fmt_currency)
            
            row_rab += 1
            no_rab += 1
            
        # Baris Grand Total RAB
        ws_rab.merge_range(f'A{row_rab+1}:F{row_rab+1}', 'GRAND TOTAL (Rp)', fmt_header)
        ws_rab.write_formula(row_rab, 6, f"=SUM(G4:G{row_rab})", fmt_bold_currency)
        
        # -------------------------------------------------------
        # SHEET TKDN (TINGKAT KOMPONEN DALAM NEGERI)
        # -------------------------------------------------------
        ws_tkdn.set_column('B:B', 30)
        ws_tkdn.write('A1', 'ANALISIS TKDN', fmt_title)
        
        for col, h in enumerate(['No', 'Komponen', 'Total Nilai (Rp)', 'Nilai Luar Negeri', 'Nilai Dalam Negeri']):
            ws_tkdn.write(3, col, h, fmt_header)
            
        ws_tkdn.write('A5', 1, fmt_border)
        ws_tkdn.write('B5', 'Material & Upah', fmt_border)
        
        # [PERBAIKAN TAHAP 1] Hapus angka hardcode 50.000.000. 
        # Gunakan rumus Excel dinamis: Ambil 25% dari Grand Total RAB sebagai porsi Upah/Lokal
        baris_terakhir_rab = row_rab
        ws_tkdn.write_formula('C5', f"=(SUM('2. RAB'!G4:G{baris_terakhir_rab}))", fmt_currency) 
        ws_tkdn.write_formula('D5', "=C5 * 0.15", fmt_currency) # Asumsi 15% impor
        ws_tkdn.write_formula('E5', "=C5 * 0.85", fmt_currency) # Asumsi 85% lokal
        
        # -------------------------------------------------------
        # SHEET 1: REKAPITULASI
        # -------------------------------------------------------
        ws_rekap.set_column('B:B', 40)
        ws_rekap.set_column('C:C', 25)
        
        ws_rekap.merge_range('A1:C1', 'REKAPITULASI BIAYA PROYEK', fmt_title)
        
        for col, h in enumerate(['No', 'Divisi Pekerjaan', 'Total Harga (Rp)']): 
            ws_rekap.write(2, col, h, fmt_header)
            
        ws_rekap.write('A4', 1, fmt_border)
        ws_rekap.write('B4', 'Pekerjaan Struktur Utama & Arsitektur', fmt_border)
        ws_rekap.write_formula('C4', f"=SUM('2. RAB'!G4:G{baris_terakhir_rab})", fmt_currency)
        
        ws_rekap.merge_range('A5:B5', 'TOTAL REKAPITULASI', fmt_header)
        ws_rekap.write_formula('C5', "=C4", fmt_bold_currency)
        
        # -------------------------------------------------------
        # FINALISASI EXCEL
        # -------------------------------------------------------
        workbook.close()
        output.seek(0)
        return output
