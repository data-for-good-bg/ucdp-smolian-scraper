import os
import logging
from scrapy.crawler import CrawlerProcess
from main_code.functions import merge_files
from main_code.functions import drop_empty_files, transform_clean_data
from main_code.functions import get_latest_merged_file
from main_code.wood_spyder import WoodSpider
#from main_code.images import create_heatmap
from settings import path, selected_files, crawl_all
from importlib import reload
reload(logging)
filename = f'{os.path.join(os.getcwd())}/logging.log'
logging.basicConfig(filename=filename,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

start_crawl = True

logging.info('>>>>> Start of UCDP SMOLIAN script')
logging.info(f'>>>>> Crawl UCDP SMOLIAN: {start_crawl} ......')


if start_crawl != True:
    pass
else:
    logging.info(f'......................SPYDER CRAWLER START......................')
    if len(selected_files) > 0:
        logging.info(f'>>>>> Total # of pre-selected files to be crawled: {len(selected_files)} ......')

    logging.info(f'>>>>> Crawl all pages: {crawl_all} ......')

    process = CrawlerProcess()
    process.crawl(WoodSpider)
    process.start()

    logging.info(f'......................SPYDER CRAWLER END......................')
    logging.info(f'>>>>> Finish craw with export path: {path.upper()} ......')
    merge_files(path=path, delete_prior=True)

#cleaning part
drop_empty_files(path='exports/archive')
extracted_urls, data = get_latest_merged_file(path=path)
logging.info(f'>>>>> # observations in latest merge: {len(data)} ......')
clean_data = transform_clean_data(data)

# creating images part
# list_variables_heatmap = ['Начална цена',
#                           'разлика от начална цена (лв.)', '%от начална цена (лв.)',
#                           'начална цена лв./м3', 'крайна цена лв./м3', 'Договорена цена (лв.)','Втора цена',
#                           'брой участници (споменати)',  'Едра', 'Средна',
#                           'Дребна', 'ОЗМ', 'Дърва за огрев', 'Обем дървесина (м3)']
#
# for variable in list_variables_heatmap:
#     create_heatmap(data_frame=clean_data, variable=variable)