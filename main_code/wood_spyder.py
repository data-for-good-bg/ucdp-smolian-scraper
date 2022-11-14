import logging
import os
from datetime import datetime
import scrapy
from main_code.functions import iserror
from main_code.functions import extract_competitors
from main_code.functions import get_latest_merged_file
from settings import selected_files
from settings import crawl_all
from settings import MAIN_PATH, path

extracted_urls, data = get_latest_merged_file(path=path)
logging.info(f'>>>>> # observations in latest merge: {len(data)} ......')

class WoodSpider(scrapy.Spider):
    name = 'spider'
    allowed_domains = ['auction.ucdp-smolian.com']
    start_urls = ['https://auction.ucdp-smolian.com/publicInfo?view=archive']
    base_url = 'https://auction.ucdp-smolian.com'

    custom_settings = {
        'FEEDS': {
            f'{os.path.join(MAIN_PATH,path)}/export_ucdp-smolian_{datetime.now()}.json': {
                'format': 'json',
                'overwrite': True
            }
        }
    }

    def parse(self, response):

        if len(selected_files)>0:
            logging.info(f'Extracting files from a selected set: {len(selected_files)}')
            all_auctions = selected_files.copy()
            for auction_url in all_auctions:
                if auction_url not in extracted_urls:
                    logging.info(f'Extracting........: {auction_url}')
                    try:
                        yield scrapy.Request(auction_url, callback=self.parse_auction)
                    except:
                        yield {'url': 'auction_url', 'ISSUE at download:': 1}

                else:
                    continue
        else:
            all_auctions = response.xpath('//tr/td/a')  # .extract()

            for auction in all_auctions:
                auction_url = auction.xpath('.//@href').extract_first()
                auction_url = self.base_url + auction_url

                if auction_url not in extracted_urls:
                    logging.info(f'Extracting........: {auction_url}')
                    try:
                        yield scrapy.Request(auction_url, callback=self.parse_auction)
                    except:
                        yield {'url': 'auction_url', 'ISSUE at download:': 1}

                else:
                    continue

            if crawl_all == True:
                string = "//tr/td/ul[@class='pagination']/li/a[contains(concat(' ', i/@class, ' '), ' fa fa-chevron-right ')]/@href"
                next_page_partial_url = response.xpath(string).extract_first()

                if next_page_partial_url:
                    next_page_url = self.base_url + next_page_partial_url
                    yield scrapy.Request(next_page_url, callback=self.parse)

    def parse_auction(self, response):

        all_content = response.xpath('//tr')
        _dict = {}

        _dict['#urls'] = len(all_content.xpath('.//td/a/@href').extract())

        for i, content in enumerate(all_content):

            ##check if there are links
            if len(content.xpath('.//td/a/@href')) != 0:
                url = content.xpath('.//td/a/@href').extract()

                if len(url) >= 1:
                    contents = content.xpath('.//td//text()').extract()  # contains titles + data
                    value = contents[0]
                    _dict[value.split(' - ')[0]] = 'https://auction.ucdp-smolian.com' + url[0]

            # if it does not contain a link
            else:
                contents = content.xpath('.//td//text()').extract()  # contains titles + data
                if len(contents) == 1:
                    value = contents[0]
                    if '\xa0' in value or 'Резултати' in value or 'Данни за дървесина' in value \
                            or 'Документация към процедурата' in value:
                        pass

                    elif i == 0:
                        _dict['ДП'] = value
                    elif 'Обект №' in value:
                        _dict['Възложител'] = value.split('/')[0]
                    else:
                        _dict[i] = contents[0]

                elif len(contents) == 2:
                    _dict[contents[0]] = contents[1]

                else:
                    new_content = []
                    for value in contents:
                        value = value.replace('\n', '').strip()
                        new_content.append(value)
                        new_content = list(filter(None, new_content))

                    for i, value in enumerate(new_content):
                        if 'първо място' in value:
                            _dict['първо място'] = value.split('На първо място')[1].strip()
                        if i == 1:
                            _dict['първа цена'] = value.split('цена в размер на ')[-1]
                        if 'второ място' in value:
                            _dict['второ място'] = value.split('На второ място')[1].strip()
                        if i == 3:
                            _dict['втора цена'] = value.split('цена в размер на ')[-1]
                        if 'трето място' in value:
                            _dict['трето място'] = value.split('На трето място')[1].strip()
                        if i == 5:
                            _dict['трета цена'] = value.split('цена в размер на ')[-1]

        # adding some additional fields
        _dict['url'] = response.url

        relevant_urls = [v for k, v in _dict.items() if "протокол" in k.lower()]

        if len(relevant_urls) == 0:
            pass
        elif len(relevant_urls) > 1:
            print(f'Multiple protocols  for {response.url}')
            _dict['участници (извлечени)'] = 'ERROR, multiple protocols'

        else:
            url = relevant_urls[0]
            competitors = extract_competitors(url, path='exports/protocols')
            _dict['брой участници (споменати)'] = competitors[0]
            _dict['участници (извлечени)'] = str(competitors[1])
            _dict['брой участници (извлечени)'] = len(competitors[1])
            _dict['страници протокол'] = competitors[2]

        fields_mapping = {'url': 'url'
            , 'ДП': 'ДП'
            , 'Възложител': 'ДГС/ДЛС'
            , 'Обект №': 'Обект№'
            , '№ търг': 'Tърг№'
            , 'Първа дата': 'Първа дата'
            , 'Втора дата': 'Втора дата'
            , 'Предмет': 'Предмет'
            , 'Начална цена': 'Начална цена'
            , 'Дървесен вид': 'Дървесен вид'
            , 'Едра': 'Едра'
            , 'Средна': 'Средна'
            , 'Дребна': 'Дребна'
            , 'ОЗМ': 'ОЗМ'
            , 'Дърва за огрев': 'Дърва за огрев'
            , 'Общо': 'Общо'
            , "първо място": 'Първо място'
            , 'първа цена': 'Първа цена'
            , 'второ място': 'Второ място'
            , 'втора цена': 'Втора цена'
            , 'брой участници (споменати)': 'брой участници (споменати)'
            , 'участници (извлечени)': 'участници (извлечени)'
            , 'брой участници (извлечени)': 'брой участници (извлечени)'
            , "Протокол": 'Протокол'
            , 'страници протокол': 'страници протокол'
            , 'Заповед': "Заповед"
            , 'Заповед за определяне на купувач': 'Заповед за определяне на купувач'
            , 'Заповед за откриване': 'Заповед за откриване'
            , 'Заповед за прекратяване': 'Заповед за прекратяване'
            , 'Договор и приложения': 'Договор'
            , 'Допълнитено споразумение': 'Допълнитено споразумение'
            , 'Изменена документация': 'Изменена документация'
            , 'Заповед за изменение': 'Заповед за изменение'
            , 'Заповед за определяне на изпълнител': 'Заповед за определяне на изпълнител'
            , 'Уведомление за прекратяване на договор': 'Уведомление за прекратяване на договор'
            , 'Приложения': 'Приложения'
            , 'Документация': 'Документация'
            , '#urls': '#документи'
                          }

        mapped = {v: iserror(k, _dict) for k, v in fields_mapping.items()}
        not_mapped = {k: v for k, v in _dict.items() if k not in [i for i in fields_mapping]}

        final_dict = {**mapped, **not_mapped} if len(not_mapped) > 0 else mapped

        yield final_dict


