import numpy as np
import pandas as pd
import os
import PyPDF2
from nltk import sent_tokenize

from datetime import datetime
from datetime import date
import json
import requests
import logging
import re

def get_latest_file(PATH,type_,aux=None):
    
    if aux==None:
        aux=''
    list_of_files = [os.path.join(PATH, file)
                     for file in os.listdir(os.path.join(PATH))
                     if type_ in file
                     and aux in file
                     and os.path.getsize(os.path.join(PATH, file)) != 0
                     ]
    latest_file=None
    data = []
    urls = []
    if len(list_of_files) != 0:
        latest_file = max(list_of_files, key=os.path.getctime)
    
        with open(latest_file ,encoding='ascii') as f:
             data = json.load(f)
                
        urls = [i['url'] for i in data]

    return latest_file, urls, data


def extract_competitors_table(url, path):
    
    #download pdf file
    response = requests.get(url)
    filename = url.split('/')[-1]
        
    mentioned_requests = np.nan
    set_requests = []
    num_pages = np.nan
    
    if '.pdf' in filename and filename not in [os.listdir(os.path.join(os.getcwd(),path))] :
        try:
            with open(f"{os.path.join(os.getcwd(),path,filename)}", 'wb') as pdf:
                pdf.write(response.content)
        except:
            logging.warn('PDF cannot be downloaded')

        #extract informtion from downloaded files
        try:
            with open(f'{os.path.join(os.getcwd(),path,filename)}','rb') as pdfFileObj:
                pdfReader = PyPDF2.PdfFileReader(pdfFileObj)

                num_pages = pdfReader.numPages
                for page in range(0, np.min([num_pages,8])):
                    pageObj = pdfReader.getPage(page)

                    try:
                        text = pageObj.extractText()

                        for sent in sent_tokenize(text):
                            if 'заучастиевтъргаот' in sent.replace(' ','') and 'броя' in sent:
#                                 print(sent)
                                mentioned_requests = int(re.findall(r'\d+ броя', sent)[0].split('броя')[0])

                    except Exception as e:
                        logging.warn(f'Error processing page: {page}: {e}')
                        print(f'Error processing page: {page}: {e}')
        except:
            logging.warn('Error processing PDFs')
            print('Error processing PDFs')   
            

    else:
        print('ERROR No pdf file provided')
    

    return [mentioned_requests,set_requests,num_pages]




def transform_clean_data(data, GLOBAL_NAME):
    ##transform data can also be a dataframe input
    if type(data) == list:
        data_frame = pd.DataFrame.from_dict(data)
    else:
        data_frame = data.copy()
    
    assert len(data_frame) == len(data),' Raw data not same length as input file'
    
    data_frame.to_excel(f'{os.path.join(os.getcwd(),"exports/excel/")}{GLOBAL_NAME}_raw_data_{datetime.now().date()}.xlsx'
                       ,index=False)
    
    clean_data = data_frame.copy()
    
    # adjusting columns
    for key in ['Начална цена','Първа цена','Втора цена']:
        for index in clean_data.index:
            new_value = np.nan
            try:
                new_value = float(clean_data[key][index].split(' ')[0])# лв без ДДС / лева без ДДС
            except:
                new_value = clean_data[key][index]

            clean_data.loc[index,key] = new_value
                
#     clean_data.loc[1,'месец']
            
    for key in ['Едра', 'Средна', 'Дребна','ОЗМ', 'Дърва за огрев', 'Общо']:
        clean_data[key] = clean_data[key].apply(lambda x: np.nan if x.split('куб.м.')[0] == ' ' or x.split('куб.м.')[0] == ''
                                                else float(x.split('куб.м.')[0]))
        

    # derived columns
    clean_data['година'] = clean_data['Втора дата'].apply(lambda x: int(x.split(' ')[0].split('.')[2]))
    clean_data['месец'] = clean_data['Втора дата'].apply(lambda x: int(x.split(' ')[0].split('.')[1]))
    clean_data['ден'] = clean_data['Втора дата'].apply(lambda x: int(x.split(' ')[0].split('.')[0]))
    clean_data['дата'] = clean_data.apply(lambda x: date(x['година'], x['месец'],x['ден']), axis = 1)
    
    if 'вид търг' in clean_data.columns:
        pass
    else:
        clean_data['вид търг'] = clean_data['Предмет'].apply(lambda x: 'електронен търг' 
                                                         if 'Електронен търг' in x 
                                                         else 'електронен конкурс' if 'Електронен конкурс' in x else x )
    if 'предмет' in clean_data.columns:
        pass
    else:
        clean_data['предмет'] = clean_data['Предмет'].apply(lambda x: 'действително добити количества' 
                                                            if 'действително добити количества' in x
                                                            else 'дървесина на прогнозни количества'  if 'дървесина на прогнозни количества' in x
                                                            else 'дървесина на корен' if 'дървесина на корен' in x
                                                            else np.nan
                                                           )
    
    clean_data['селище'] = clean_data['ДГС/ДЛС'].apply(lambda x: x.split(' ')[2] if x.split(' ')[-1] == '' else x.split(' ')[-1])
    clean_data['ДГС/ДЛС'] = clean_data['ДГС/ДЛС'].apply(lambda x: x.split(' ')[1])
    
    for key in ['ДП', 'ДГС/ДЛС','селище', 'Обект№', 'Tърг№']:
        clean_data[key]=clean_data[key].apply(lambda x:x.strip())
    
    # calculated fields
    clean_data['разлика от начална цена (лв.)'] = clean_data['Първа цена'] - clean_data['Начална цена']
    clean_data['%от начална цена (лв.)'] = clean_data['Първа цена']/clean_data['Начална цена']
    clean_data['%увеличение'] = clean_data['разлика от начална цена (лв.)']/clean_data['Начална цена']
    
    clean_data['начална цена лв./м3'] = clean_data['Начална цена'] / clean_data['Общо']
    clean_data['крайна цена лв./м3'] = clean_data['Първа цена'] / clean_data['Общо']
    
    # to float
    
    for key in ['Начална цена','разлика от начална цена (лв.)','%от начална цена (лв.)'
                ,'начална цена лв./м3','крайна цена лв./м3', 'Първа цена','Втора цена', 'брой участници (споменати)'
                ,'Едра', 'Средна', 'Дребна','ОЗМ', 'Дърва за огрев', 'Общо']:
        clean_data[key] = clean_data[key].apply(lambda x: float(x))
        
    if 'други коментари' not in clean_data.columns:
        clean_data['други коментари']=np.nan
    
    # Sense checks: purva cena >= vtora cena
    clean_data = clean_data[['дата','година', 'месец', 'ден','url', 'ДП', 'ДГС/ДЛС','селище', 'Обект№', 'Tърг№'
                             ,'вид търг','предмет', 'Начална цена','разлика от начална цена (лв.)','%от начална цена (лв.)'
                             ,'%увеличение','начална цена лв./м3','крайна цена лв./м3', 'Първа цена','Втора цена'
                             ,'Първо място','Второ място', 'брой участници (споменати)','участници (извлечени)'
                             , 'брой участници (извлечени)','Дървесен вид', 'Едра', 'Средна', 'Дребна','ОЗМ'
                             , 'Дърва за огрев', 'Общо','други коментари'
                            ]]

    
    #change name of columns
    clean_data.rename(columns = {'Общо':'Обем дървесина (м3)'},inplace = True)
    clean_data.rename(columns = {'Първа цена':'Договорена цена (лв.)'},inplace = True)
    
    assert len(clean_data) == len(data), 'Some values have dropped while cleaning, please check'
    
    clean_data.to_excel(f'{os.path.join(os.getcwd(),"exports/excel/")}{GLOBAL_NAME}_clean_data_{datetime.now().date()}.xlsx'
                       ,index=False)
    return clean_data 