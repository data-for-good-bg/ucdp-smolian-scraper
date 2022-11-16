import os
import numpy as np
import pandas as pd
import logging
import json
import requests
import PyPDF2
import re
from datetime import datetime
from datetime import date
from nltk import sent_tokenize

from settings import MAIN_PATH

# additional functions
def iserror(value, dict_):
    try:
        output = dict_[value]
    except KeyError:
        output = np.nan
    return output


def drop_empty_files(path='exports/archive'):
    # drop empty files
    empty_files = [os.path.join(MAIN_PATH, path, file) for file in os.listdir(os.path.join(MAIN_PATH, path))
                   if '.json' in file
                   and os.path.getsize(os.path.join(MAIN_PATH, path, file)) == 0]

    for file in empty_files:
        os.remove(file)


def merge_files(path='exports/archive', delete_prior=False):
    logging.info(f'Start of procedure to merge UCDP export at [{path.upper()}], delete_prior = {delete_prior}')

    # delete previously merged files
    if delete_prior is True:
        merged_files = [os.path.join(MAIN_PATH, path, file)
                        for file in os.listdir(os.path.join(MAIN_PATH, path))
                        if 'merged_' in file and '.json' in file]

        for file in merged_files:
            os.remove(file)

        logging.info(f'#merged files removed: {len(merged_files)}')

    # get all relevant files that need to be merged
    list_of_exports = [os.path.join(MAIN_PATH, path, file)
                       for file in os.listdir(os.path.join(MAIN_PATH, path))
                       if 'export_' in file and '.json' in file
                       and os.path.getsize(os.path.join(MAIN_PATH, path, file)) != 0
                       ]
    if len(list_of_exports) == 0:
        logging.info(f'No files to merge')
    else:
        logging.info(f'Merging all previously downloaded files: #{len(list_of_exports)}')

        merged_set = []
        for filename in list_of_exports:
            with open(filename, encoding='ascii') as f:
                data = json.load(f)
                for file in data:
                    if file not in merged_set:
                        merged_set.append(file)

        new_filename = f'merged_ucdp-smolian_{datetime.now()}.json'
        with open(os.path.join(MAIN_PATH, path, new_filename), 'w') as f:
            json.dump(merged_set, f)

        logging.info(f'Updated merged file (#{len(merged_set)}) created at {path}: {new_filename} ')


def get_latest_merged_file(path='exports/archive'):
    urls = []
    list_of_files = [os.path.join(MAIN_PATH, path, file)
                     for file in os.listdir(os.path.join(MAIN_PATH, path))
                     if 'merged_' in file and '.json' in file
                     and os.path.getsize(os.path.join(MAIN_PATH, path, file)) != 0
                     ]

    if len(list_of_files) != 0:
        latest_file = max(list_of_files, key=os.path.getctime)
        with open(latest_file, encoding='ascii') as f:
            data = json.load(f)

        urls = [i['url'] for i in data]
    else:
        data = []
        pass

    return urls, data


def transform_clean_data(data):
    data_frame = pd.DataFrame.from_dict(data)

    assert len(data_frame) == len(data), ' Raw data not same length as input file'

    data_frame.to_excel(f'{os.path.join(MAIN_PATH, "exports/excel/")}raw_data_{datetime.now().date()}.xlsx'
                        , index=False)

    clean_data = data_frame.copy()

    # adjusting columns
    for key in ['Начална цена', 'Първа цена', 'Втора цена']:
        for index in clean_data.index:
            new_value = np.nan
            try:
                new_value = float(clean_data[key][index].split(' ')[0])  # лв без ДДС / лева без ДДС
            except:
                new_value = clean_data[key][index]

            clean_data.loc[index, key] = new_value

    for key in ['Едра', 'Средна', 'Дребна', 'ОЗМ', 'Дърва за огрев', 'Общо']:
        clean_data[key] = clean_data[key].apply(
            lambda x: np.nan if x.split('куб.м.')[0] == ' ' else float(x.split('куб.м.')[0]))

    # derived columns
    clean_data['година'] = clean_data['Втора дата'].apply(lambda x: int(x.split(' ')[0].split('.')[2]))
    clean_data['месец'] = clean_data['Втора дата'].apply(lambda x: int(x.split(' ')[0].split('.')[1]))
    clean_data['ден'] = clean_data['Втора дата'].apply(lambda x: int(x.split(' ')[0].split('.')[0]))
    clean_data['дата'] = clean_data.apply(lambda x: date(x['година'], x['месец'], x['ден']), axis=1)

    clean_data['вид търг'] = clean_data['Предмет'].apply(lambda x: 'електронен търг'
    if 'Електронен търг' in x
    else 'електронен конкурс' if 'Електронен конкурс' in x else x)

    clean_data['предмет'] = clean_data['Предмет'].apply(lambda x: 'действително добити количества'
    if 'действително добити количества' in x
    else 'дървесина на прогнозни количества' if 'дървесина на прогнозни количества' in x
    else 'дървесина на корен' if 'дървесина на корен' in x
    else np.nan
                                                        )

    clean_data['селище'] = clean_data['ДГС/ДЛС'].apply(
        lambda x: x.split(' ')[2] if x.split(' ')[-1] == '' else x.split(' ')[-1])
    clean_data['ДГС/ДЛС'] = clean_data['ДГС/ДЛС'].apply(lambda x: x.split(' ')[1])
    clean_data['МТ индикатор'] = clean_data['Обект№'].apply(lambda x: 1 if 'МТ' in x or "MT" in x else 0)

    # calculated fields
    clean_data['разлика от начална цена (лв.)'] = clean_data['Първа цена'] - clean_data['Начална цена']
    clean_data['%от начална цена (лв.)'] = clean_data['Първа цена'] / clean_data['Начална цена'] - 1
    clean_data['начална цена лв./м3'] = clean_data['Начална цена'] / clean_data['Общо']
    clean_data['крайна цена лв./м3'] = clean_data['Първа цена'] / clean_data['Общо']

    # to float
    for key in ['Начална цена', 'разлика от начална цена (лв.)', '%от начална цена (лв.)'
        , 'начална цена лв./м3', 'крайна цена лв./м3', 'Първа цена', 'Втора цена', 'брой участници (споменати)'
        , 'Едра', 'Средна', 'Дребна', 'ОЗМ', 'Дърва за огрев', 'Общо']:
        clean_data[key] = clean_data[key].apply(lambda x: float(x))

    # Sense checks: purva cena >= vtora cena
    clean_data = clean_data[['дата', 'година', 'месец', 'ден', 'url', 'ДП', 'ДГС/ДЛС', 'селище', 'Обект№','МТ индикатор'
        , 'Tърг№', 'вид търг', 'предмет', 'Начална цена', 'разлика от начална цена (лв.)', '%от начална цена (лв.)'
        , 'начална цена лв./м3', 'крайна цена лв./м3', 'Първа цена', 'Втора цена'
        , 'Първо място', 'Второ място', 'брой участници (споменати)', 'участници (извлечени)'
        , 'брой участници (извлечени)', 'Дървесен вид', 'Едра', 'Средна', 'Дребна', 'ОЗМ'
        , 'Дърва за огрев', 'Общо'
                             ]]

    # change name of columns
    clean_data.rename(columns={'Общо': 'Обем дървесина (м3)'}, inplace=True)
    clean_data.rename(columns={'Първа цена': 'Договорена цена (лв.)'}, inplace=True)

    assert len(clean_data) == len(data), 'Some values have dropped while cleaning, please check'
    clean_data.to_excel(f'{os.path.join(MAIN_PATH, "exports/excel/")}clean_data_{datetime.now().date()}.xlsx'
                        , index=False)
    return clean_data


def extract_competitors(url, path='exports/protocols'):
    # download pdf file
    response = requests.get(url)
    filename = url.split('/')[-1]

    if '.pdf' in filename:
        pass
    else:
        return ['ERROR No pdf file provided']

    with open(f"{os.path.join(MAIN_PATH, path, filename)}", 'wb') as pdf:
        pdf.write(response.content)

    # extract informtion from downloaded file
    with open(f'{os.path.join(MAIN_PATH, path, filename)}', 'rb') as pdfFileObj:
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)

        mentioned_requests = np.nan
        set_requests = []

        # checking first 8 pages
        num_pages = pdfReader.numPages
        for page in range(0, np.min([num_pages, 8])):
            pageObj = pdfReader.getPage(page)

            try:
                text = pageObj.extractText()
                text = text.replace('Заявка с Вх. №', 'Заявка с Вх №')
                text = text.replace('както следва:', 'както следва.')

                text_filtered = text.replace(' ', '').replace('\n', '')
                if 'неерегистрираннитоединучастник' in text_filtered and 'ЗаявкасВх№' not in text:
                    #                     set_requests.append('не е регистриран нито един участник')
                    pass
                else:
                    for sent in sent_tokenize(text):
                        if 'заучастиесапостъпили' in sent.replace(' ', '') and 'броя' in sent:
                            mentioned_requests = int(re.findall(r'\d+ броя', sent)[0].split('броя')[0])
                        if 'Заявка с Вх №' in sent:
                            request = sent.split('депозирана от ')[-1]
                            set_requests.append(request)
            except:
                print(f'Protocol: {filename} ..... Error with text on page: {page + 1}')
                continue

    return [mentioned_requests, set_requests, num_pages]