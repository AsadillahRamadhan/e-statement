import tabula
import pandas as pd
import numpy as np
from PyPDF2 import PdfReader
import locale
import re
import os
import traceback
import pdfplumber
import warnings
warnings.filterwarnings("ignore", message=".*CropBox missing.*")


class PDFEstatementProcessor:
    def __init__(self):
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        pd.options.mode.chained_assignment = None

    def process_pdf_file(self, pdf_path, BankCode, transfer_data, name, nik, mobile_phone, source, bank_code, email, email_pass, user, user_pass, account_list):
        pandas_dfs = []
        saldo_awal = 0
        saldo = 0
        period_thn = 0

        def get_month(text):
            bulan_list = ['JANUARI', 'FEBRUARI', 'MARET', 'APRIL', 'MEI', 'JUNI',
                'JULI', 'AGUSTUS', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DESEMBER']
            pattern = r'(' + '|'.join(bulan_list) + r')\s+(\d{4})'
            match = re.search(pattern, text)
            if match:
                bulan = match.group(1).upper()
                tahun = match.group(2)
                return f"{bulan} {tahun}"
            return None

        def get_account_number(text):
            match = re.search(r'NO\.?\s*REKENING\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
            if match:
                no_rekening = match.group(1)
                return no_rekening
            return None
        
        reader = PdfReader(pdf_path)
        number_of_pages = len(reader.pages)

        with pdfplumber.open(pdf_path) as pdf:
                
                

            for i in range(0, number_of_pages):
                page = pdf.pages[i]
                dfs = page.extract_text().split('\n')
                dfhead_text = page.extract_text()
                # dfs = tabula.read_pdf(pdf_path, pages=i, area=(230, 0, 1000, 1000), columns=[30, 78.82, 296, 331, 460.70])   
                # dfhead_text = ' '.join(dfhead.astype(str).fillna('').values.flatten())
                # print(dfhead[0])

                list_pattern = r'(\d{2}/\d{2})\s+(.*?)\s+([\d,]+\.\d{2})(?:\s+(DB|CR))?(?:\s+([\d,]+\.\d{2}))?'

                matched_data = []
                for data in dfs:
                    match = re.match(list_pattern, data)
                    if match:
                        keterangan = match.group(2)
                        for i in range(dfs.index(data) + 1, len(dfs)):
                            match_detail = re.match(list_pattern, dfs[i])
                            if not match_detail:
                                keterangan = " ".join([keterangan, dfs[i]])
                            else:
                                break

                        matched_data.append({
                            'TANGGAL': match.group(1),
                            'KETERANGAN': keterangan,
                            'CBG': '-',
                            'MUTASI': f"{match.group(3)}{f' {match.group(4)}' if match.group(4) else ''}",
                            'SALDO': f'{match.group(5)}' if match.group(5) else ''
                        })
                dfs = pd.DataFrame(matched_data)

                an = name.upper()
                no_rek = get_account_number(dfhead_text)
                PERIODE = get_month(dfhead_text)
                period_thn = PERIODE.split(' ')[1] if ' ' in PERIODE else ''


                # if period_thn == '':
                #     print(dfhead)
                #     an = dfhead[0].iloc[0].index.tolist()[0]
                #     no_rek = dfhead[0].iloc[0].index.tolist()[7]
                #     period_thn = dfhead[0].iloc[2].iloc[-1].split(' ')[1] if not pd.isna(dfhead[0].iloc[2].iloc[-1]) else dfhead[0].iloc[2].iloc[-4].split(' ')[1]

                # df = dfs[0]
                # if i == 1:
                #     saldo_awal = df[df['KETERANGAN'] == 'SALDO AWAL']['SALDO'].values[0]
                #     if not isinstance(saldo_awal, float):
                #         saldo = float(saldo_awal.replace(',', ''))
                #     df = df[df['KETERANGAN'] != 'SALDO AWAL']
                
                # try:
                #     df = df[df['MUTASI'] != 'Bersambung ke Halaman berikut']
                # except:
                #     pass
                
                # df1 = df.drop('Unnamed: 0', axis=1)
                # merged_keterangan = df1['KETERANGAN'].fillna('').groupby(df1['TANGGAL'].notna().cumsum()).transform(' '.join)
                # df1.loc[df['TANGGAL'].isna(), 'KETERANGAN'] = merged_keterangan
                # df1 = df1[df1['TANGGAL'].notna()]
                # df1.reset_index(drop=True, inplace=True)

                # df2 = df.drop('Unnamed: 0', axis=1)
                # df2['KETERANGAN'] = df2.groupby(df2['TANGGAL'].notna().cumsum())['KETERANGAN'].apply(lambda x: ' '.join(x.dropna()))
                # df2.dropna(subset=['KETERANGAN'], inplace=True)
                # df2.reset_index(drop=True, inplace=True)
                # df1['KETERANGAN'] = df2['KETERANGAN']

                # if i == number_of_pages - 1:
                #     pattern = r"SALDO AWAL :.*$"
                #     df1['KETERANGAN'] = df1['KETERANGAN'].apply(lambda x: re.sub(pattern, '', x))

                # df1.insert(0, 'no_rek', no_rek)
                # df1.insert(1, 'nama_rek', an)
                # df1.insert(2, 'mata_uang', 'IDR')
                # df1.insert(3, 'periode', PERIODE)
                # df1.insert(8, 'DBCR', df1['MUTASI'].apply(lambda x: 'DB' if 'DB' in str(x) else 'CR'))

                # df1['MUTASI'] = df1['MUTASI'].str.replace('DB', '').str.replace(',', '').astype(float)
                
                # df1.insert(0, 'no_rek', no_rek)
                # df1.insert(1, 'nama_rek', an)
                # df1.insert(2, 'mata_uang', 'IDR')
                # df1.insert(3, 'periode', PERIODE)

                dfs['no_rek'] = no_rek
                dfs['nama_rek'] = an
                dfs['mata_uang'] = 'IDR'
                dfs['periode'] = PERIODE
                dfs['SALDO'] = '-'
                dfs['DBCR'] = dfs['MUTASI'].apply(lambda x: 'DB' if 'DB' in str(x) else 'CR')
                dfs['MUTASI'] = dfs['MUTASI'].str.replace('DB', '').str.replace(',', '').astype(float)

                def calculate_saldo(row):
                    nonlocal saldo
                    if row['DBCR'] == 'CR':
                        saldo += row['MUTASI']
                    elif row['DBCR'] == 'DB':
                        saldo -= row['MUTASI']
                    return round(saldo, 2)

                # df1['SALDO'] = df1.apply(calculate_saldo, axis=1)

                # if i == number_of_pages - 1:
                #     dfakhir = tabula.read_pdf(pdf_path, pages=i, area=(230, 0, 1000, 1000), columns=[30, 78.82, 460.70])
                #     saldo_akhr = dfakhir[0].iloc[-1, 2].split(':')[1].strip().replace(',', '')

                pandas_dfs.append(dfs)

        result = pd.concat(pandas_dfs, ignore_index=True)
        result.rename(columns={'KETERANGAN': 'keterangan', 'CBG': 'cbg', 'MUTASI': 'jumlah', 'SALDO': 'saldo', 'TANGGAL': 'tanggal'}, inplace=True)
        result.replace('nan', np.nan, inplace=True)
        result.dropna(subset=['jumlah', 'saldo'], inplace=True)

        # Format tanggal dd/mm/YYYY & format angka x,xxx,xxx,xxx.00
        # result['tanggal'] = result['tanggal'] + '/' + period_thn
        # result['jumlah'] = result['jumlah'].apply(lambda x: locale.format_string("%.2f", x, grouping=True)).astype(str)
        # result['saldo'] = result['saldo'].apply(lambda x: locale.format_string("%.2f", x, grouping=True)).astype(str)

        # Format tanggal dd/MMMM/YYYY & format angka x,xxx,xxx,xxx (tanpa .00)
        result['tanggal'] = pd.to_datetime(
            result['tanggal'] + '/' + period_thn,
            format='%d/%m/%Y',
            errors='coerce'
        ).dt.strftime('%d-%b-%Y')
        result['jumlah'] = result['jumlah'].apply(lambda x: locale.format_string("%d", round(float(x)), grouping=True))
        # result['saldo'] = result['saldo'].apply(lambda x: locale.format_string("%d", round(float(x)), grouping=True))

        def extract_transaction_info(row):
            keterangan = row['keterangan'].upper()
            direction = row['DBCR']
            nominal = row['jumlah']
            a_number = row['no_rek']
            a_name = row['nama_rek']
            tanggal = row['tanggal']

            print(tanggal, keterangan)

            b_number = '-'
            b_nik = '-'
            b_name = '-'
            b_mobile = '-'
            b_email_pass = '-'
            b_user_pass = '-'
            b_bank_code = bank_code
            b_bank_name = source
            a_nik = nik
            a_mobile = mobile_phone

            if 'BI-FAST' in keterangan:
                match = re.findall(r'BI-FAST\s+(DB|CR)\s+BIF\s+(TRANSFER)\s+KE\s+(\d+)\s+(.*)\s+KBB', keterangan)
                if match:
                    b_name = match[0][3]
                    bank = BankCode.query.filter(BankCode.bank_code == match[0][2]).first()
                    if(bank):
                        b_bank_code = bank.bank_code
                        b_bank_name = bank.bank_name
                else:
                    match = re.findall(r'BI-FAST\s+(DB|CR)\s+BIF\s+(TRANSFER)\s+DR\s+(\d+)\s+(.*)', keterangan)
                    if match:
                        b_name = match[0][3]
                        bank = BankCode.query.filter(BankCode.bank_code == match[0][2]).first()
                        if(bank):
                            b_bank_code = bank.bank_code
                            b_bank_name = bank.bank_name
                    else:
                        match = re.findall(r'BI-FAST\s+(DB|CR)\s+BIF\s+(TRANSFER)\s+DR\s+TANGGAL\s+\:\d{2}\/\d{2}\s+(\d+)\s+(.*)', keterangan)
                        if match:
                            b_name = match[0][3]
                            bank = BankCode.query.filter(BankCode.bank_code == match[0][2]).first()
                            if(bank):
                                b_bank_code = bank.bank_code
                                b_bank_name = bank.bank_name
                            else:
                                return pd.Series(dtype=object)
            elif 'TRSF E-BANKING' in keterangan:
                match = re.findall(r"TRSF E-BANKING\s+(CR|DB)\s+(.*)\s+(\d+).\d+\s+(.*)", keterangan)
                if(match):
                    b_name = match[0][3]
                else:
                    match = re.findall(r"TRSF E-BANKING\s+(CR|DB)\s+(.*)\s+:*(\d{2}\/\d{2})\s+(.*)", keterangan)
                    if(match):
                        b_name = match[0][3]
                    else:
                        match = re.findall(r"TRSF E-BANKING\s+(CR|DB)\s+(\d{2}\/\d{2})\s+[\w/\\]+\s+(.*)", keterangan)
                        if(match):
                            b_name = match[0][2]
                        else:
                            return pd.Series(dtype=object)
            elif 'SWITCHING' in keterangan:
                match = re.findall(r"SWITCHING\s+.*\s+(\d+)\s+(.*)", keterangan)
                if(match):
                    b_name = match[0][1]
                    bank = BankCode.query.filter(BankCode.bank_code == match[0][0]).first()
                    if(bank):
                        b_bank_code = bank.bank_code
                        b_bank_name = bank.bank_name
            elif 'BANK OF CHINA' in keterangan:
                match = re.findall(r".*\s+LLG-BANK OF CHINA\s+(.*)", keterangan)
                if(match):
                    b_name = match[0]
            else:

                return pd.Series(dtype=object)


            
            trans_type = re.split(r'\s+\d{3,}|KE\s+\d{3,}|DARI\s+\d{3,}', keterangan)[0].strip()

            # if trans_type == "SWITCHING DB TRANSFER" or trans_type == 'SWITCHING CR DR':
            #     return pd.Series(dtype=object)

            if trans_type == "SWITCHING DB TRANSFER":
                return pd.Series(dtype=object)

            for index, account in account_list.iterrows():
                if pd.isna(account['% B Bank Name']):
                    continue
                if account['% B name'].strip() in b_name.strip() and account['% B Bank Name'].strip() in b_bank_name.strip():
                    account = account.fillna('-')
                    b_name, b_number, b_nik, b_mobile, b_email_pass, b_user_pass = account['% B name'] , account['% B number'], account['% B NIK'], account['% B Mobile'], account['% B Email Pass'], account['% B User Pass']
                    
            return pd.Series({
                '% date': tanggal,
                '% nominal': nominal,
                '% A number': a_number,
                '% A Bank Code': bank_code,
                '% A Bank Name': source,
                '% A NIK': a_nik,
                '% A name': name,
                '% A Mobile': a_mobile,
                '% A Email Pass': f"{email}:{email_pass}",
                '% A User Pass': f"{user}:{user_pass}",
                '% B number': b_number,
                '% B Bank Code': b_bank_code,
                '% B Bank Name': b_bank_name,
                '% B NIK': b_nik,
                '% B name': b_name,
                '% B Mobile': b_mobile,
                '% B Email Pass': b_email_pass,
                '% B User Pass': b_user_pass,
                '% Keterangan': keterangan,
                '% Transactiontype': trans_type,
                '% Direction': direction
            })
        if result.empty:
            final_result = pd.DataFrame([{
                '% date': "",
                '% nominal': "",
                '% A number': "",
                '% A Bank Code': "",
                '% A Bank Name': "",
                '% A NIK': "",
                '% A name': "",
                '% A Mobile': "",
                '% A Email Pass': "",
                '% A User Pass': "",
                '% B number': "",
                '% B Bank Code': "",
                '% B Bank Name': "",
                '% B NIK': "",
                '% B name': "",
                '% B Mobile': "",
                '% B Email Pass': "",
                '% B User Pass': "",
                '% Keterangan': "",
                '% Transactiontype': "",
                '% Direction': ""
            }])
            is_av = False
        else:
            final_result = result.apply(extract_transaction_info, axis=1)
            final_result = final_result[final_result.notna().all(axis=1)]
            is_av = True
        return is_av, final_result, None

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
                    error_details = traceback.format_exc()
                    print(error_details)  # atau logging.error(error_details)
                    return f"Error processing CSV data: {str(e)}"

    def process_file(self, file_path):
        try:
            result, saldo_akhr = self.process_pdf_file(file_path)
            result.to_csv(file_path.replace('.pdf', '.csv'), index=False)

            df_cleaned = result.dropna(subset=['% nominal'])
            sld = df_cleaned.tail(1)

            print(f"No Rekening: {result['% B number'].iloc[-1]}\tSaldo Akhir: {saldo_akhr}")
        except Exception as e:
            error_details = traceback.format_exc()
            print(error_details)  # atau logging.error(error_details)
            return f"Error processing CSV data: {str(e)}"
