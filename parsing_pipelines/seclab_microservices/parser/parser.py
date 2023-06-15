from core.parser.parser import Parser, ParserConfig, IEntityModel
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from os import environ
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from logging import getLogger
from datetime import datetime

import config
import asyncio

logger = getLogger(__name__)


SECURITYLAB_NEW_URL = 'https://www.securitylab.com'


def href_filter(href: str) -> Optional[str]:
    news_slug = '/news'
    php_extension = '.php'

    if href.startswith(SECURITYLAB_NEW_URL) and href.endswith(php_extension):
        return href
    elif href.startswith(news_slug) and href.endswith(php_extension):
        return href
    else:
        return None


def init_parser_cfg() -> ParserConfig:
    input_queue = environ.get(config.INPUT_QUEUE_NAME_KEY)
    output_queue = environ.get(config.OUTPUT_QUEUE_NAME_KEY)
    downloader_queue = environ.get(config.DOWNLOADER_QUEUE)
    mq_host = environ.get(config.MQ_HOST_KEY)
    mq_port = int(environ.get(config.MQ_PORT_KEY))
    mq_user = environ.get(config.MQ_USER_KEY)
    mq_pass = environ.get(config.MQ_PASS_KEY)
    return ParserConfig(
        input_queue_name=input_queue,
        output_queue_name=output_queue,
        downloader_queue=downloader_queue,
        mq_host=mq_host,
        mq_port=mq_port,
        mq_user=mq_user,
        mq_pass=mq_pass,
        href_filter=href_filter
    )


class SecuritylabNewsEntityModel(IEntityModel):
    def __init__(self,
                 date: datetime,
                 author: str,
                 title: str,
                 tags: List[str],
                 text: str
                 ):
        self.date = date
        self.author = author
        self.title = title
        self.tags = tags
        self.text = text

    def serialize(self) -> Dict:
        return {
            'date': self.date,
            'author': self.author,
            'title': self.title,
            'tags': self.tags,
            'text': self.text
        }


def safety_extract_text(bs_object, default: str) -> str:
    try:
        return bs_object.text
    except Exception:
        return default


class SecuritylabParser(Parser):
    async def extract_entities(self, html_page: str) -> List[IEntityModel]:
        try:
            soup = BeautifulSoup(html_page, 'html.parser')
            date = datetime.fromisoformat(soup.find('time').get('datetime'))
            author = safety_extract_text(soup.find('div', itemprop='author'), '')
            title = soup.title.string
            tags_div = soup.find('div', class_='article-tags')
            tags = [safety_extract_text(tag, '') for tag in tags_div.find_all('a', class_='tag')]
            text_div = soup.find('div', itemprop='description')
            if text_div:
                text_tokens = text_div.find_all('p')
                text = ''.join(token.get_text() for token in text_tokens)
            else:
                text_tokens = soup.find('div', class_='articl-text')
                text = ''.join(token.get_text() for token in text_tokens)
            return [
                        SecuritylabNewsEntityModel(
                            date,
                            author,
                            title,
                            tags,
                            text
                        )
                    ]
        except Exception as e:
            logger.error(f'Parsing error: {e}')
            return []


async def main():
    cfg = init_parser_cfg()
    parser = SecuritylabParser(cfg)
    await parser.run()


if __name__ == "__main__":
    logger.info('[+] Securitylab parser started')
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', seconds=config.INTERVAL, id='seclab_parser',
                      max_instances=config.MAX_INSTANCES)
    scheduler.start()
    asyncio.get_event_loop().run_forever()
