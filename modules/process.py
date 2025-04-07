import tabula
import pandas as pd
import numpy as np
from PyPDF2 import PdfReader
import locale
import re
import os

class PDFEstatementProcessor:
    def __init__(self):
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        pd.options.mode.chained_assignment = None

    def process_pdf_file(self, pdf_path):
        pandas_dfs = []
        saldo_awal = 0
        saldo = 0
        period_thn = 0

        reader = PdfReader(pdf_path)
        number_of_pages = len(reader.pages) + 1

        for i in range(1, number_of_pages):
            dfs = tabula.read_pdf(pdf_path, pages=i, area=(230, 0, 1000, 1000), columns=[30, 78.82, 296, 331, 460.70])
            dfhead = tabula.read_pdf(pdf_path, pages=i, area=(80, 0, 230, 1000))
            an = dfhead[0].iloc[0, 0]
            no_rek = dfhead[0].iloc[0, 3]
            PERIODE = dfhead[0].iloc[4, 3]
            period_thn = PERIODE.split(' ')[1]

            df = dfs[0]
            if i == 1:
                saldo_awal = df[df['KETERANGAN'] == 'SALDO AWAL']['SALDO'].values[0]
                saldo = float(saldo_awal.replace(',', ''))
                df = df[df['KETERANGAN'] != 'SALDO AWAL']
            
            try:
                df = df[df['MUTASI'] != 'Bersambung ke Halaman berikut']
            except:
                pass
            
            df1 = df.drop('Unnamed: 0', axis=1)
            merged_keterangan = df1['KETERANGAN'].fillna('').groupby(df1['TANGGAL'].notna().cumsum()).transform(' '.join)
            df1.loc[df['TANGGAL'].isna(), 'KETERANGAN'] = merged_keterangan
            df1 = df1[df1['TANGGAL'].notna()]
            df1.reset_index(drop=True, inplace=True)

            df2 = df.drop('Unnamed: 0', axis=1)
            df2['KETERANGAN'] = df2.groupby(df2['TANGGAL'].notna().cumsum())['KETERANGAN'].apply(lambda x: ' '.join(x.dropna()))
            df2.dropna(subset=['KETERANGAN'], inplace=True)
            df2.reset_index(drop=True, inplace=True)
            df1['KETERANGAN'] = df2['KETERANGAN']

            if i == number_of_pages - 1:
                pattern = r"SALDO AWAL :.*$"
                df1['KETERANGAN'] = df1['KETERANGAN'].apply(lambda x: re.sub(pattern, '', x))

            df1.insert(0, 'no_rek', no_rek)
            df1.insert(1, 'nama_rek', an)
            df1.insert(2, 'mata_uang', 'IDR')
            df1.insert(3, 'periode', PERIODE)
            df1.insert(8, 'DBCR', df1['MUTASI'].apply(lambda x: 'DB' if 'DB' in str(x) else 'CR'))

            df1['MUTASI'] = df1['MUTASI'].str.replace('DB', '').str.replace(',', '').astype(float)

            def calculate_saldo(row):
                nonlocal saldo
                if row['DBCR'] == 'CR':
                    saldo += row['MUTASI']
                elif row['DBCR'] == 'DB':
                    saldo -= row['MUTASI']
                return round(saldo, 2)

            df1['SALDO'] = df1.apply(calculate_saldo, axis=1)

            if i == number_of_pages - 1:
                dfakhir = tabula.read_pdf(pdf_path, pages=i, area=(230, 0, 1000, 1000), columns=[30, 78.82, 460.70])
                saldo_akhr = dfakhir[0].iloc[-1, 2].split(':')[1].strip().replace(',', '')

            pandas_dfs.append(df1)

        result = pd.concat(pandas_dfs, ignore_index=True)
        result.rename(columns={'KETERANGAN': 'keterangan', 'CBG': 'cbg', 'MUTASI': 'jumlah', 'SALDO': 'saldo', 'TANGGAL': 'tanggal'}, inplace=True)
        result.replace('nan', np.nan, inplace=True)
        result.dropna(subset=['jumlah', 'saldo'], inplace=True)

        result['tanggal'] = result['tanggal'] + '/' + period_thn
        result['jumlah'] = result['jumlah'].apply(lambda x: locale.format_string("%.2f", x, grouping=True)).astype(str)
        result['saldo'] = result['saldo'].apply(lambda x: locale.format_string("%.2f", x, grouping=True)).astype(str)

        def extract_transaction_info(row):
            keterangan = row['keterangan'].upper()
            direction = row['DBCR']
            nominal = row['jumlah']
            b_number = row['no_rek']
            b_name = row['nama_rek']
            tanggal = row['tanggal']

            a_number = '-'
            a_nik = '-'
            a_name = '-'
            a_mobile = '-'
            b_nik = '-'
            b_mobile = '-'

            if 'BI-FAST' in keterangan:
                match = re.findall(r'BI-FAST\s+(DB|CR)\s+BIF\s+(TRANSFER)\s+KE\s+(\d+)\s+(.*)\s+KBB', keterangan)
                if match:
                    a_name = match[0][3]
                else:
                    match = re.findall(r'BI-FAST\s+(DB|CR)\s+BIF\s+(TRANSFER)\s+DR\s+(\d+)\s+(.*)', keterangan)
                    if match:
                        a_name = match[0][3]
                    else:
                        return
            elif 'TRSF E-BANKING' in keterangan:
                match = re.findall(r"TRSF E-BANKING\s+(CR|DB)\s+(.*)\s+(\d+).\d+\s+(.*)", keterangan)
                if(match):
                    a_name = match[0][3]
            elif 'SWITCHING' in keterangan:
                match = re.findall(r"SWITCHING\s+.*\s+\d+\s+(.*)", keterangan)
                if(match):
                    a_name = match[0]
            elif 'BANK OF CHINA' in keterangan:
                match = re.findall(r".*\s+LLG-BANK OF CHINA\s+(.*)", keterangan)
                if(match):
                    a_name = match[0]
            else:

                return None

            trans_type = re.split(r'\s+\d{3,}|KE\s+\d{3,}|DARI\s+\d{3,}', keterangan)[0].strip()

            if(trans_type == "SWITCHING DB TRANSFER"):
                return None

            return pd.Series({
                '% date': tanggal,
                '% nominal': nominal,
                '% A number': a_number,
                '% A NIK': a_nik,
                '% A name': a_name,
                '% A Mobile': a_mobile,
                '% B number': b_number,
                '% B NIK': b_nik,
                '% B name': b_name,
                '% B Mobile': b_mobile,
                '% Transactiontype': trans_type,
                '% Direction': direction
            })

        final_result = result.apply(extract_transaction_info, axis=1)
        final_result = final_result[final_result.notna().all(axis=1)]
        return final_result, saldo_akhr.replace(',', '')

    def process_files_in_directory(self, directory):
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in [f for f in filenames if f.endswith(".pdf")]:
                pdf_path = os.path.join(dirpath, filename)
                try:
                    result, saldo_akhr = self.process_pdf_file(pdf_path)
                    result.to_csv(filename.replace('.pdf', '.csv'), index=False)

                    df_cleaned = result.dropna(subset=['% nominal'])
                    sld = df_cleaned.tail(1)

                    print(f"No Rekening: {result['% B number'].iloc[-1]}\tSaldo Akhir: {saldo_akhr}")
                except Exception as e:
                    print(e)
                    print(f"Error processing file: {filename}")

    def process_file(self, file_path):
        try:
            result, saldo_akhr = self.process_pdf_file(file_path)
            result.to_csv(file_path.replace('.pdf', '.csv'), index=False)

            df_cleaned = result.dropna(subset=['% nominal'])
            sld = df_cleaned.tail(1)

            print(f"No Rekening: {result['% B number'].iloc[-1]}\tSaldo Akhir: {saldo_akhr}")
        except Exception as e:
            print(e)
            print(f"Error processing file: {file_path}")
