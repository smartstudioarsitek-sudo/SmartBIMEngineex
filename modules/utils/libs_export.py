# modules/utils/libs_export.py
import pandas as pd
from io import BytesIO
import xlsxwriter

class Export_Engine:
    def __init__(self):
        pass

    def create_dxf(self, drawing_type, params):
        dxf = "0\nSECTION\n2\nENTITIES\n"
        def add_line(x1, y1, x2, y2, layer="STRUKTUR"):
            return f"0\nLINE\n8\n{layer}\n10\n{x1}\n20\n{y1}\n30\n0.0\n11\n{x2}\n21\n{y2}\n31\n0.0\n"
        def add_text(x, y, text, height=0.15, layer="TEXT"):
            return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n30\n0.0\n40\n{height}\n1\n{text}\n"
        
        if drawing_type == "BALOK":
            b = params['b'] / 1000; h = params['h'] / 1000
            dxf += add_line(0, 0, b, 0) + add_line(b, 0, b, h) + add_line(b, h, 0, h) + add_line(0, h, 0, 0)
            dxf += add_text(b/2-0.1, -0.2, "Detail Balok")
        dxf += "0\nENDSEC\n0\nEOF"
        return dxf


    def generate_7tab_rab_excel(self, project_name="Proyek Strategis Nasional", df_boq=None, price_engine=None):
        
        # --- [INJEKSI RUMUS BPJS PP 44/2015] ---
        def hitung_bpjs_berjenjang(nilai_kontrak_tanpa_ppn):
            sisa_nilai = nilai_kontrak_tanpa_ppn
            bpjs_total = 0.0
            if sisa_nilai > 0:
                potongan = min(sisa_nilai, 100000000); bpjs_total += potongan * 0.0024; sisa_nilai -= potongan
            if sisa_nilai > 0:
                potongan = min(sisa_nilai, 400000000); bpjs_total += potongan * 0.0019; sisa_nilai -= potongan
            if sisa_nilai > 0:
                potongan = min(sisa_nilai, 500000000); bpjs_total += potongan * 0.0015; sisa_nilai -= potongan
            if sisa_nilai > 0:
                potongan = min(sisa_nilai, 4000000000); bpjs_total += potongan * 0.0012; sisa_nilai -= potongan
            if sisa_nilai > 0:
                bpjs_total += sisa_nilai * 0.0010
            return bpjs_total

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # --- DEFINISI FORMAT ---
        fmt_title = workbook.add_format({'bold': True, 'font_size': 14})
        fmt_header = workbook.add_format({'bold': True, 'bg_color': '#1E3A8A', 'font_color': 'white', 'border': 1, 'align': 'center'})
        fmt_border = workbook.add_format({'border': 1})
        fmt_currency = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1})
        fmt_currency_bold = workbook.add_format({'num_format': 'Rp #,##0', 'border': 1, 'bold': True, 'bg_color': '#D1D5DB'})
        
        # --- MEMBUAT 7 SHEET ---
        ws_rekap = workbook.add_worksheet('1. Rekap')
        ws_rab = workbook.add_worksheet('2. RAB')
        ws_boq = workbook.add_worksheet('3. Backup BOQ')
        ws_ahsp = workbook.add_worksheet('4. AHSP S2 30 2025')
        ws_smkk = workbook.add_worksheet('5. SMKK')
        ws_tkdn = workbook.add_worksheet('6. TKDN')
        ws_bp = workbook.add_worksheet('7. Basic Price')

        # =======================================================
        # TAB 7: BASIC PRICE (TERINTEGRASI 3-TIER ENGINE - AUDIT READY)
        # =======================================================
        ws_bp.write('A1', 'DAFTAR HARGA DASAR MATERIAL, UPAH, DAN ALAT', fmt_title)
        
        headers_bp = ['No', 'Kategori', 'Nama Material / Upah', 'Satuan', 'Harga Satuan (Rp)', 'Sumber Data (Validasi Auditor)']
        for col, h in enumerate(headers_bp): ws_bp.write(2, col, h, fmt_header)
        
        ws_bp.set_column('C:C', 35)
        ws_bp.set_column('E:E', 20)
        ws_bp.set_column('F:F', 90) # Dibuat sangat lebar agar URL Scraping muat

        # --- LOGIKA EKSTRAKSI MATERIAL OTOMATIS DARI AHSP ---
        import sys
        kebutuhan_unik = {} 
        try:
            # Ambil modul AHSP yang sudah menyala di memori aplikasi
            mod_ahsp = sys.modules.get('libs_ahsp')
            if mod_ahsp:
                # Cari otomatis Class apapun yang menyimpan buku resep 'koefisien'
                for item_name in dir(mod_ahsp):
                    item = getattr(mod_ahsp, item_name)
                    if isinstance(item, type): # Jika dia adalah Class
                        try:
                            instance = item()
                            if hasattr(instance, 'koefisien'): # Ketemu Otaknya!
                                for key, resep in instance.koefisien.items():
                                    for nama_bahan, qty in resep.get("bahan", {}).items():
                                        if "(" in nama_bahan and ")" in nama_bahan:
                                            nama_bersih = nama_bahan.split("(")[0].strip()
                                            satuan = nama_bahan.split("(")[1].replace(")", "").strip()
                                        else:
                                            nama_bersih = nama_bahan
                                            satuan = "Ls/Unit"
                                        kebutuhan_unik[nama_bersih] = ("Bahan", satuan)
                                    
                                    for nama_upah, qty in resep.get("upah", {}).items():
                                        kebutuhan_unik[nama_upah] = ("Upah", "OH")
                                break # Berhenti mencari kalau sudah ketemu
                        except:
                            pass
        except Exception as e:
            pass # Aman, tidak akan crash meskipun gagal
                       
        row_bp = 3
        idx = 1
        for nama_item, (kategori, satuan) in kebutuhan_unik.items():
            harga_angka = 0
            sumber_teks = "Manual Input"
            
            # PANGGIL MESIN PENCARI HARGA!
            if price_engine:
                harga_angka, sumber_teks = price_engine.get_best_price(nama_item, lokasi="Lampung")
                
            ws_bp.write(row_bp, 0, idx, fmt_border)
            ws_bp.write(row_bp, 1, kategori, fmt_border)
            ws_bp.write(row_bp, 2, nama_item, fmt_border)
            ws_bp.write(row_bp, 3, satuan, fmt_border)
            ws_bp.write(row_bp, 4, harga_angka, fmt_currency)
            
            if "Toko Online" in sumber_teks:
                ws_bp.write(row_bp, 5, sumber_teks, workbook.add_format({'border': 1, 'font_color': '#1D4ED8'}))
            else:
                ws_bp.write(row_bp, 5, sumber_teks, fmt_border)
            
            row_bp += 1
            idx += 1
            
        last_row_basic = row_bp - 1

        # =======================================================
        # TAB 4: AHSP (DINAMIS MENCETAK SELURUH BUKU RESEP)
        # =======================================================
        ws_ahsp.set_column('A:A', 15)
        ws_ahsp.set_column('B:B', 35)
        ws_ahsp.set_column('C:D', 12)
        ws_ahsp.set_column('E:F', 18)
        ws_ahsp.write('A1', 'ANALISA HARGA SATUAN PEKERJAAN (AHSP)', fmt_title)
        
        row_ahsp = 3
        
        # Iterasi seluruh resep yang ada di mesin AHSP
        for kode_ahsp, resep in mesin_ahsp.koefisien.items():
            # Judul Pekerjaan
            ws_ahsp.write(row_ahsp, 0, f"Item Pekerjaan: {resep.get('desc', kode_ahsp)}", workbook.add_format({'bold': True, 'font_color': '#1E3A8A'}))
            row_ahsp += 1
            
            # Header Tabel AHSP
            for col, h in enumerate(['Kategori', 'Uraian', 'Koefisien', 'Satuan', 'Harga Dasar', 'Subtotal']): 
                ws_ahsp.write(row_ahsp, col, h, fmt_header)
            row_ahsp += 1
            
            start_row = row_ahsp + 1
            
            # 1. Tulis Baris Bahan
            for bahan, qty in resep.get("bahan", {}).items():
                nama_b = bahan.split("(")[0].strip() if "(" in bahan else bahan
                sat = bahan.split("(")[1].replace(")","").strip() if "(" in bahan else "Ls"
                ws_ahsp.write(row_ahsp, 0, 'Bahan', fmt_border)
                ws_ahsp.write(row_ahsp, 1, nama_b, fmt_border)
                ws_ahsp.write(row_ahsp, 2, float(qty), fmt_border)
                ws_ahsp.write(row_ahsp, 3, sat, fmt_border)
                # Vlookup ke Tab 7
                ws_ahsp.write_formula(row_ahsp, 4, f'=IFERROR(VLOOKUP("*{nama_b}*","\'7. Basic Price\'!C:E", 3, FALSE), 0)', fmt_currency)
                ws_ahsp.write_formula(row_ahsp, 5, f"=C{row_ahsp+1}*E{row_ahsp+1}", fmt_currency)
                row_ahsp += 1
                
            # 2. Tulis Baris Upah
            for upah, qty in resep.get("upah", {}).items():
                ws_ahsp.write(row_ahsp, 0, 'Upah', fmt_border)
                ws_ahsp.write(row_ahsp, 1, upah, fmt_border)
                ws_ahsp.write(row_ahsp, 2, float(qty), fmt_border)
                ws_ahsp.write(row_ahsp, 3, 'OH', fmt_border)
                ws_ahsp.write_formula(row_ahsp, 4, f'=IFERROR(VLOOKUP("*{upah}*","\'7. Basic Price\'!C:E", 3, FALSE), 0)', fmt_currency)
                ws_ahsp.write_formula(row_ahsp, 5, f"=C{row_ahsp+1}*E{row_ahsp+1}", fmt_currency)
                row_ahsp += 1
                
            # Total Harga Satuan Pekerjaan
            ws_ahsp.write(row_ahsp, 4, 'Total Harga Satuan', fmt_header)
            # Proteksi error jika analisa kosong
            if row_ahsp >= start_row:
                ws_ahsp.write_formula(row_ahsp, 5, f"=SUM(F{start_row}:F{row_ahsp})", fmt_currency_bold)
            else:
                ws_ahsp.write(row_ahsp, 5, 0, fmt_currency_bold)
                
            row_ahsp += 3 # Jarak antar tabel analisa
               
        # =======================================================
        # TAB 3 & 2: INJEKSI DATA ASLI IFC (DINAMIS)
        # =======================================================
        ws_boq.set_column('B:C', 30)
        ws_boq.write('A1', 'BACKUP BILL OF QUANTITIES (BOQ) DARI BIM IFC', fmt_title)
        for col, h in enumerate(['No', 'Kategori IFC', 'Nama Elemen', 'Volume (m3)']): ws_boq.write(2, col, h, fmt_header)

        ws_rab.set_column('B:B', 40)
        ws_rab.write('A1', f'RENCANA ANGGARAN BIAYA (RAB) - {project_name.upper()}', fmt_title)
        for col, h in enumerate(['No', 'Elemen Struktur', 'Volume', 'Satuan', 'Harga Satuan (Rp)', 'Total Harga (Rp)']): ws_rab.write(2, col, h, fmt_header)

        if df_boq is None or df_boq.empty:
            df_boq = pd.DataFrame([{"Kategori": "IfcColumn", "Nama": "Kolom K1 (Upload IFC untuk data asli)", "Volume": 64.0}])

        baris_terakhir_rab = 3

        for index, row in df_boq.iterrows():
            row_excel = index + 3 
            
            # Tab 3
            ws_boq.write(row_excel, 0, index + 1, fmt_border)
            ws_boq.write(row_excel, 1, str(row['Kategori']), fmt_border)
            ws_boq.write(row_excel, 2, str(row['Nama']), fmt_border)
            ws_boq.write(row_excel, 3, float(row['Volume']), fmt_border)
            
            # Tab 2
            ws_rab.write(row_excel, 0, index + 1, fmt_border)
            ws_rab.write(row_excel, 1, f"Pengecoran {row['Nama']}", fmt_border)
            ws_rab.write_formula(row_excel, 2, f"='3. Backup BOQ'!D{row_excel+1}", fmt_border)
            ws_rab.write(row_excel, 3, 'm3', fmt_border)
            ws_rab.write_formula(row_excel, 4, "='4. AHSP S2 30 2025'!F7", fmt_currency)
            ws_rab.write_formula(row_excel, 5, f"=C{row_excel+1}*E{row_excel+1}", fmt_currency)
            baris_terakhir_rab = row_excel

        ws_rab.write(baris_terakhir_rab + 1, 4, 'TOTAL BIAYA STRUKTUR', fmt_header)
        ws_rab.write_formula(baris_terakhir_rab + 1, 5, f"=SUM(F4:F{baris_terakhir_rab+1})", fmt_currency_bold)

        # =======================================================
        # TAB 1: REKAPITULASI (Termasuk PPN)
        # =======================================================
        ws_rekap.set_column('B:B', 35)
        ws_rekap.write('A1', 'REKAPITULASI BIAYA PROYEK', fmt_title)
        for col, h in enumerate(['No', 'Divisi Pekerjaan', 'Total Harga (Rp)']): ws_rekap.write(2, col, h, fmt_header)
        
        ws_rekap.write('A4', 1, fmt_border)
        ws_rekap.write('B4', 'Pekerjaan Struktur', fmt_border)
        ws_rekap.write_formula('C4', f"='2. RAB'!F{baris_terakhir_rab + 2}", fmt_currency)
        
        ws_rekap.write('B6', 'A. TOTAL BIAYA FISIK', fmt_header)
        ws_rekap.write_formula('C6', "=SUM(C4:C4)", fmt_currency_bold)
        
        ws_rekap.write('B7', 'B. PPN 11%', fmt_header)
        ws_rekap.write_formula('C7', "=C6 * 0.11", fmt_currency_bold) 
        
        ws_rekap.write('B8', 'C. GRAND TOTAL (A + B)', fmt_header)
        ws_rekap.write_formula('C8', "=C6 + C7", fmt_currency_bold)

        # =======================================================
        # TAB 5: SMKK (STANDAR 9 KOMPONEN + BPJS DINAMIS)
        # =======================================================
        ws_smkk.set_column('B:B', 60)
        ws_smkk.write('A1', 'RENCANA BIAYA PENERAPAN SISTEM MANAJEMEN KESELAMATAN KONSTRUKSI (SMKK)', fmt_title)
        
        estimasi_rab_awal = df_boq['Volume'].sum() * 500000 
        nilai_bpjs_aktual = hitung_bpjs_berjenjang(estimasi_rab_awal)

        headers_smkk = ['No', 'Uraian Pekerjaan', 'Satuan', 'Volume', 'Harga Satuan (Rp)', 'Total Harga (Rp)']
        for col, h in enumerate(headers_smkk): ws_smkk.write(2, col, h, fmt_header)
        
        smkk_items = [
            ("1. Penyiapan RKK, RKPPL, RMLLP, dan RMPK", "", "", "", ""),
            ("   a. Pembuatan Dokumen SMKK (RKK, RMPK, RKPPL)", "Set", 1, 250000, "=D5*E5"),
            ("2. Sosialisasi, Promosi, dan Pelatihan", "", "", "", ""),
            ("   a. Spanduk (Banner) K3", "Lbr", 1, 150000, "=D7*E7"),
            ("   b. Papan Informasi K3", "Bh", 1, 250000, "=D8*E8"),
            ("3. Alat Pelindung Kerja (APK) dan APD", "", "", "", ""),
            ("   a. Topi Pelindung (Safety Helmet)", "Bh", 5, 65000, "=D11*E11"),
            ("   b. Sepatu Keselamatan (Safety Shoes)", "Psg", 5, 160000, "=D12*E12"),
            ("   c. Rompi Keselamatan (Safety Vest)", "Bh", 5, 45000, "=D13*E13"),
            ("4. Asuransi dan Perizinan", "", "", "", ""),
            ("   a. BPJS Ketenagakerjaan (Sektor Konstruksi PP 44/2015)", "Ls", 1, nilai_bpjs_aktual, "=D16*E16"),
            ("5. Personel K3 Konstruksi", "", "", "", ""),
            ("   a. Petugas Keselamatan Konstruksi (Tingkat Risiko Kecil)", "OB", 1, 2500000, "=D19*E19"),
            ("6. Fasilitas Sarana, Prasarana, dan Alat Kesehatan", "", "", "", ""),
            ("   a. Peralatan P3K (Kotak P3K Lengkap)", "Ls", 1, 300000, "=D22*E22"),
            ("7. Rambu-Rambu dan Barikade", "", "", "", ""),
            ("   a. Rambu Peringatan (Warning Sign)", "Ls", 1, 250000, "=D25*E25"),
            ("8. Konsultasi dengan Ahli Keselamatan", "", "", "", ""),
            ("   a. (Tidak diwajibkan untuk Risiko Kecil)", "Ls", 0, 0, 0),
            ("9. Kegiatan Pengendalian Risiko", "", "", "", ""),
            ("   a. Alat Pemadam Api Ringan (APAR) 3 Kg", "Bh", 1, 450000, "=D30*E30")
        ]
        
        row_smkk = 3
        for item in smkk_items:
            if item[1] == "":
                ws_smkk.write(row_smkk, 0, "", fmt_border)
                ws_smkk.write(row_smkk, 1, item[0], workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E5E7EB'}))
                ws_smkk.write_blank(row_smkk, 2, "", fmt_border)
                ws_smkk.write_blank(row_smkk, 3, "", fmt_border)
                ws_smkk.write_blank(row_smkk, 4, "", fmt_border)
                ws_smkk.write_blank(row_smkk, 5, "", fmt_border)
            else:
                ws_smkk.write(row_smkk, 0, "", fmt_border)
                ws_smkk.write(row_smkk, 1, item[0], fmt_border) 
                ws_smkk.write(row_smkk, 2, item[1], fmt_border) 
                ws_smkk.write(row_smkk, 3, item[2], fmt_border) 
                ws_smkk.write(row_smkk, 4, item[3], fmt_currency) 
                ws_smkk.write_formula(row_smkk, 5, str(item[4]), fmt_currency) 
            row_smkk += 1
            
        ws_smkk.write(row_smkk, 1, 'TOTAL BIAYA SMKK', fmt_header)
        ws_smkk.write_formula(row_smkk, 5, f"=SUM(F4:F{row_smkk})", fmt_currency_bold)

        # =======================================================
        # TAB 6: TKDN (Tingkat Komponen Dalam Negeri)
        # =======================================================
        ws_tkdn.set_column('B:B', 30)
        ws_tkdn.set_column('C:E', 22)
        ws_tkdn.write('A1', 'PERHITUNGAN TINGKAT KOMPONEN DALAM NEGERI (TKDN)', fmt_title)
        
        headers_tkdn = ['No', 'Kategori Komponen', 'KDN (Dalam Negeri)', 'KLN (Luar Negeri)', 'Total Biaya (Rp)']
        for col, h in enumerate(headers_tkdn): ws_tkdn.write(2, col, h, fmt_header)
        
        ws_tkdn.write('A4', 1, fmt_border)
        ws_tkdn.write('B4', 'Bahan / Material Struktur', fmt_border)
        ws_tkdn.write_formula('E4', f"='2. RAB'!F{baris_terakhir_rab + 2}", fmt_currency) 
        ws_tkdn.write_formula('C4', "=E4 * 0.85", fmt_currency) 
        ws_tkdn.write_formula('D4', "=E4 * 0.15", fmt_currency) 
        
        ws_tkdn.write('A5', 2, fmt_border)
        ws_tkdn.write('B5', 'Tenaga Kerja & Upah', fmt_border)
        ws_tkdn.write('E5', 50000000, fmt_currency) 
        ws_tkdn.write_formula('C5', "=E5 * 1.0", fmt_currency) 
        ws_tkdn.write('D5', 0, fmt_currency)
        
        ws_tkdn.write(5, 1, 'TOTAL', fmt_header)
        ws_tkdn.write_formula(5, 2, "=SUM(C4:C5)", fmt_currency_bold)
        ws_tkdn.write_formula(5, 3, "=SUM(D4:D5)", fmt_currency_bold)
        ws_tkdn.write_formula(5, 4, "=SUM(E4:E5)", fmt_currency_bold)
        
        fmt_percent = workbook.add_format({'num_format': '0.00" %"', 'bold': True, 'border': 1, 'bg_color': '#D1D5DB', 'align': 'center'})
        ws_tkdn.write(7, 1, 'NILAI TKDN PROYEK (%) =', fmt_header)
        ws_tkdn.write_formula(7, 2, "=(C6/E6)*100", fmt_percent)

        workbook.close()
        return output.getvalue()
    









