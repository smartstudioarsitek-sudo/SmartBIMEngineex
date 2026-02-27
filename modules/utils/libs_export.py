import pandas as pd
from io import BytesIO
import xlsxwriter
import sys

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

    def generate_7tab_rab_excel(self, project_name="Proyek Strategis Nasional", df_boq=None, price_engine=None, lokasi_proyek="Lampung"):
        from io import BytesIO
        import xlsxwriter
        import pandas as pd
        import streamlit as st

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
        
        # --- MEMBUAT 7 SHEET KEMBALI UTUH ---
        ws_rekap = workbook.add_worksheet('1. Rekap')
        ws_rab = workbook.add_worksheet('2. RAB')
        ws_boq = workbook.add_worksheet('3. Backup BOQ')
        ws_ahsp = workbook.add_worksheet('4. AHSP S2 30 2025')
        ws_smkk = workbook.add_worksheet('5. SMKK')
        ws_tkdn = workbook.add_worksheet('6. TKDN')
        ws_bp = workbook.add_worksheet('7. Basic Price')

        df_master = st.session_state.get('master_ahsp_data', None)
        kebutuhan_unik = {} 
        resep_ahsp_aktif = {} 

        # 1. PARSING DATA MASTER DARI MEMORI WEB
        if df_master is not None and not df_master.empty:
            for index, row in df_master.iterrows():
                desc = str(row.get('Deskripsi', ''))
                kategori = str(row.get('Kategori', '')).upper()
                komponen = str(row.get('Nama_Komponen', ''))
                satuan = str(row.get('Satuan', ''))
                koef = float(row.get('Koefisien', 0.0))
                
                # Mengumpulkan Unik untuk Tab 7
                if komponen not in kebutuhan_unik:
                    kat_display = "Bahan"
                    if "UPAH" in kategori or "PEKERJA" in kategori: kat_display = "Upah"
                    elif "ALAT" in kategori: kat_display = "Alat"
                    kebutuhan_unik[komponen] = (kat_display, satuan)
                
                # Mengumpulkan Resep untuk Tab 4
                if desc not in resep_ahsp_aktif:
                    resep_ahsp_aktif[desc] = {"desc": desc, "bahan": {}, "upah": {}, "alat": {}}
                
                if "UPAH" in kategori or "PEKERJA" in kategori:
                    resep_ahsp_aktif[desc]["upah"][komponen] = (koef, satuan)
                elif "ALAT" in kategori:
                    resep_ahsp_aktif[desc]["alat"][komponen] = (koef, satuan)
                else:
                    resep_ahsp_aktif[desc]["bahan"][komponen] = (koef, satuan)

        # =======================================================
        # TAB 7: BASIC PRICE (DENGAN IKK BPS OTOMATIS)
        # =======================================================
        ws_bp.write('A1', f'DAFTAR HARGA DASAR MATERIAL & UPAH (IKK {lokasi_proyek.upper()})', fmt_title)
        headers_bp = ['No', 'Kategori', 'Nama Material / Upah', 'Satuan', 'Harga Satuan (Rp)', 'Sumber Data']
        for col, h in enumerate(headers_bp): ws_bp.write(2, col, h, fmt_header)
        
        ws_bp.set_column('C:C', 35); ws_bp.set_column('E:E', 20); ws_bp.set_column('F:F', 40)
                
        row_bp = 3
        idx = 1
        map_baris_bp = {} # PENYELAMAT ANTI VLOOKUP: Simpan posisi persis barisnya

        for nama_item, (kategori, satuan) in kebutuhan_unik.items():
            harga_angka = 0
            sumber_teks = "Ketik Manual"
            
            # KONEKSI KE BPS ENGINE
            if price_engine:
                harga_bps, sumber_bps = price_engine.get_best_price(nama_item, lokasi=lokasi_proyek)
                if harga_bps > 0:
                    harga_angka = harga_bps
                    sumber_teks = sumber_bps

            ws_bp.write(row_bp, 0, idx, fmt_border)
            ws_bp.write(row_bp, 1, kategori, fmt_border)
            ws_bp.write(row_bp, 2, nama_item, fmt_border)
            ws_bp.write(row_bp, 3, satuan, fmt_border)
            ws_bp.write(row_bp, 4, harga_angka, fmt_currency)
            
            if harga_angka > 0:
                ws_bp.write(row_bp, 5, sumber_teks, workbook.add_format({'border': 1, 'font_color': '#1D4ED8'}))
            else:
                ws_bp.write(row_bp, 5, sumber_teks, fmt_border)
            
            # Kunci posisi baris item ini
            map_baris_bp[nama_item] = row_bp + 1 
            row_bp += 1
            idx += 1

        # =======================================================
        # TAB 4: AHSP (LINK LANGSUNG KE TAB 7)
        # =======================================================
        ws_ahsp.set_column('A:A', 15); ws_ahsp.set_column('B:B', 35); ws_ahsp.set_column('C:D', 12); ws_ahsp.set_column('E:F', 18)
        ws_ahsp.write('A1', 'ANALISA HARGA SATUAN PEKERJAAN (AHSP)', fmt_title)
        
        ws_ahsp.write('H1', 'REKAPITULASI HARGA SATUAN AHSP', fmt_title)
        ws_ahsp.set_column('H:H', 50); ws_ahsp.set_column('I:I', 10); ws_ahsp.set_column('J:J', 20)
        for col, h in enumerate(['Nama Pekerjaan / AHSP', 'Satuan', 'Harga Satuan (Rp)']): ws_ahsp.write(2, col+7, h, fmt_header)
        
        row_ahsp = 3
        row_rekap = 3
        map_baris_rekap = {} 
        
        if not resep_ahsp_aktif:
            ws_ahsp.write(row_ahsp, 0, "Buku Resep AHSP Kosong", fmt_header)
        else:
            for desc, resep in resep_ahsp_aktif.items():
                ws_ahsp.write(row_ahsp, 0, f"Item: {desc}", workbook.add_format({'bold': True, 'font_color': '#1E3A8A'}))
                row_ahsp += 1
                
                for col, h in enumerate(['Kategori', 'Uraian', 'Koefisien', 'Satuan', 'Harga Dasar', 'Subtotal']): 
                    ws_ahsp.write(row_ahsp, col, h, fmt_header)
                row_ahsp += 1
                
                start_row = row_ahsp + 1
                
                # Fungsi tulis baris dengan LINK LANGSUNG
                def tulis_komponen(kategori_nama, dict_data):
                    nonlocal row_ahsp
                    for nama_k, (koef, sat) in dict_data.items():
                        ws_ahsp.write(row_ahsp, 0, kategori_nama, fmt_border)
                        ws_ahsp.write(row_ahsp, 1, nama_k, fmt_border)
                        ws_ahsp.write(row_ahsp, 2, koef, fmt_border)
                        ws_ahsp.write(row_ahsp, 3, sat, fmt_border)
                        
                        # LINK TEMBAK LANGSUNG KE SEL TAB 7
                        if nama_k in map_baris_bp:
                            ws_ahsp.write_formula(row_ahsp, 4, f"='7. Basic Price'!E{map_baris_bp[nama_k]}", fmt_currency)
                        else:
                            ws_ahsp.write(row_ahsp, 4, 0, fmt_currency)
                            
                        ws_ahsp.write_formula(row_ahsp, 5, f"=C{row_ahsp+1}*E{row_ahsp+1}", fmt_currency)
                        row_ahsp += 1

                tulis_komponen('Bahan', resep['bahan'])
                tulis_komponen('Upah', resep['upah'])
                tulis_komponen('Alat', resep['alat'])
                    
                ws_ahsp.write(row_ahsp, 4, 'Total Harga Satuan', fmt_header)
                ws_ahsp.write_formula(row_ahsp, 5, f"=SUM(F{start_row}:F{row_ahsp})", fmt_currency_bold)
                    
                # INJEKSI KE TABEL REKAP & SIMPAN POSISINYA
                ws_ahsp.write(row_rekap, 7, desc, fmt_border)
                ws_ahsp.write(row_rekap, 8, "Ls/m3", fmt_border)
                ws_ahsp.write_formula(row_rekap, 9, f"=F{row_ahsp+1}", fmt_currency)
                
                map_baris_rekap[desc] = row_rekap + 1 
                row_rekap += 1
                row_ahsp += 3 

        # =======================================================
        # TAB 3 & 2: INJEKSI DATA RAB DENGAN LINK LANGSUNG
        # =======================================================
        ws_boq.set_column('B:C', 30)
        ws_boq.write('A1', 'BACKUP BILL OF QUANTITIES (BOQ)', fmt_title)
        for col, h in enumerate(['No', 'Kategori', 'Nama Elemen', 'Volume (m3)']): ws_boq.write(2, col, h, fmt_header)

        ws_rab.set_column('B:B', 40); ws_rab.set_column('E:E', 45) 
        ws_rab.write('A1', f'RENCANA ANGGARAN BIAYA (RAB) - {project_name.upper()}', fmt_title)
        
        headers_rab = ['No', 'Elemen Struktur', 'Volume', 'Satuan', 'Referensi AHSP', 'Harga Satuan (Rp)', 'Total Harga (Rp)']
        for col, h in enumerate(headers_rab): ws_rab.write(2, col, h, fmt_header)

        if df_boq is None or df_boq.empty:
            df_boq = pd.DataFrame([{"Kategori": "Data Manual", "Nama": "Item Kosong", "Volume": 0.0, "Referensi AHSP": ""}])

        baris_terakhir_rab = 3

        for index, row in df_boq.iterrows():
            row_excel = index + 3 
            nama_elemen = str(row.get('Nama', ''))
            vol_elemen = float(row.get('Volume', 0))
            ref_ahsp = str(row.get('Referensi AHSP', ''))
            
            ws_rab.write(row_excel, 0, index + 1, fmt_border)
            ws_rab.write(row_excel, 1, nama_elemen, fmt_border)
            ws_rab.write(row_excel, 2, vol_elemen, fmt_border)
            ws_rab.write(row_excel, 3, 'm3', fmt_border)
            ws_rab.write(row_excel, 4, ref_ahsp, fmt_border)
            
            # LINK TEMBAK LANGSUNG KE REKAP TAB 4
            if ref_ahsp in map_baris_rekap:
                ws_rab.write_formula(row_excel, 5, f"='4. AHSP S2 30 2025'!J{map_baris_rekap[ref_ahsp]}", fmt_currency)
            else:
                ws_rab.write(row_excel, 5, 0, fmt_currency)
                
            ws_rab.write_formula(row_excel, 6, f"=C{row_excel+1}*F{row_excel+1}", fmt_currency)
            baris_terakhir_rab = row_excel

        # =======================================================
        # TAB 5: SMKK (DIBUAT DINAMIS BERDASARKAN SKALA PROYEK)
        # =======================================================
        ws_smkk.set_column('B:B', 60)
        ws_smkk.write('A1', 'RENCANA BIAYA PENERAPAN SISTEM MANAJEMEN KESELAMATAN KONSTRUKSI (SMKK)', fmt_title)
        
        for col, h in enumerate(['No', 'Uraian Pekerjaan', 'Satuan', 'Volume', 'Harga Satuan (Rp)', 'Total Harga (Rp)']): ws_smkk.write(2, col, h, fmt_header)
        
        # [PERBAIKAN AUDIT]: Buat proporsi SMKK dinamis. Total fisik ditarik dari RAB.
        # Kita estimasikan SMKK sekitar 1.5% dari Total RAB sebagai basis perhitungan item.
        formula_total_rab = f"SUM('2. RAB'!G4:G{baris_terakhir_rab + 1})"
        
        # Mengunci formula Excel agar item SMKK otomatis menyesuaikan skala RAB
        smkk_items = [
            ("1. Penyiapan RKK, RKPPL, RMLLP, dan RMPK", "", "", "", ""),
            ("   a. Pembuatan Dokumen SMKK", "Set", 1, f"=({formula_total_rab})*0.001", "=D5*E5"),
            ("2. Sosialisasi, Promosi, dan Pelatihan", "", "", "", ""),
            ("   a. Spanduk & Papan Informasi", "Ls", 1, f"=({formula_total_rab})*0.0005", "=D8*E8"),
            ("3. Alat Pelindung Kerja (APK) dan APD", "", "", "", ""),
            ("   a. Set APD Lengkap (Helm, Sepatu, Rompi)", "Paket", f"=ROUNDUP(MAX(10, ({formula_total_rab})/100000000), 0)", 350000, "=D11*E11"),
            ("4. Personel K3 Konstruksi", "", "", "", ""),
            ("   a. Petugas Keselamatan Konstruksi", "OB", f"=MAX(1, ROUNDUP(({formula_total_rab})/500000000, 0))", 3500000, "=D14*E14")
        ]
        
        row_smkk = 3
        for item in smkk_items:
            if item[1] == "":
                ws_smkk.write(row_smkk, 0, "", fmt_border)
                ws_smkk.write(row_smkk, 1, item[0], workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E5E7EB'}))
                for c in range(2, 6): ws_smkk.write_blank(row_smkk, c, "", fmt_border)
            else:
                ws_smkk.write(row_smkk, 0, "", fmt_border)
                ws_smkk.write(row_smkk, 1, item[0], fmt_border) 
                ws_smkk.write(row_smkk, 2, item[1], fmt_border) 
                
                # Handling formula vs value untuk Volume (Kolom 3) dan Harga (Kolom 4)
                if str(item[2]).startswith("="): ws_smkk.write_formula(row_smkk, 3, item[2], fmt_border)
                else: ws_smkk.write(row_smkk, 3, item[2], fmt_border)
                
                if str(item[3]).startswith("="): ws_smkk.write_formula(row_smkk, 4, item[3], fmt_currency)
                else: ws_smkk.write(row_smkk, 4, item[3], fmt_currency)
                
                ws_smkk.write_formula(row_smkk, 5, str(item[4]), fmt_currency) 
            row_smkk += 1
            
        ws_smkk.write(row_smkk, 1, 'TOTAL BIAYA SMKK', fmt_header)
        ws_smkk.write_formula(row_smkk, 5, f"=SUM(F4:F{row_smkk})", fmt_currency_bold)

        # =======================================================
        # TAB 6: TKDN (PERBAIKAN HARGA DUMMY 50 JUTA)
        # =======================================================
        # ... (kode awal setup sheet tetap sama)
        ws_tkdn.write('A5', 2, fmt_border)
        ws_tkdn.write('B5', 'Tenaga Kerja & Upah', fmt_border)
        # [PERBAIKAN AUDIT]: Jangan gunakan 50000000. Ambil estimasi 25% dari total RAB untuk porsi Upah.
        ws_tkdn.write_formula('E5', f"=(SUM('2. RAB'!G4:G{baris_terakhir_rab + 1})) * 0.25", fmt_currency) 
        ws_tkdn.write_formula('C5', "=E5 * 1.0", fmt_currency) 
        ws_tkdn.write('D5', 0, fmt_currency)
        

        # =======================================================
        # TAB 1: REKAPITULASI
        # =======================================================
        ws_rekap.set_column('B:B', 35)
        ws_rekap.write('A1', 'REKAPITULASI BIAYA PROYEK', fmt_title)
        for col, h in enumerate(['No', 'Divisi Pekerjaan', 'Total Harga (Rp)']): ws_rekap.write(2, col, h, fmt_header)
        
        ws_rekap.write('A4', 1, fmt_border)
        ws_rekap.write('B4', 'Pekerjaan Struktur Utama', fmt_border)
        ws_rekap.write_formula('C4', f"=SUM('2. RAB'!G4:G{baris_terakhir_rab + 1})", fmt_currency)
        
        ws_rekap.write('B6', 'A. TOTAL BIAYA FISIK', fmt_header)
        ws_rekap.write_formula('C6', "=SUM(C4:C4)", fmt_currency_bold)
        
        ws_rekap.write('B7', 'B. PPN 11%', fmt_header)
        ws_rekap.write_formula('C7', "=C6 * 0.11", fmt_currency_bold) 
        
        ws_rekap.write('B8', 'C. GRAND TOTAL (A + B)', fmt_header)
        ws_rekap.write_formula('C8', "=C6 + C7", fmt_currency_bold)

        workbook.close()
        return output.getvalue()









