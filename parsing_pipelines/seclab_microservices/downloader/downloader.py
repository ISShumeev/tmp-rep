from typing import Optional, Dict
from os import environ
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from urllib.parse import urljoin

from logging import getLogger
from core.downloader.downloader import (
    Downloader,
    DownloaderConfig,
    DownloaderError,
    ServerIsBeingUpdatedError,
    BadRequestError,
    NotFoundError,
    ServerError,
    ClientError,
)

import config
import asyncio

SECURITYLAB_DOMAIN = 'www.securitylab.ru'
NEWS_URI = '/news'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13.4; rv:109.0) Gecko/20100101 Firefox/114.0'
}

logger = getLogger(__name__)


def init_downloader_cfg(headers: Dict) -> DownloaderConfig:
    input_queue = environ.get(config.INPUT_QUEUE_NAME_KEY)
    output_queue = environ.get(config.OUTPUT_QUEUE_NAME_KEY)
    mq_host = environ.get(config.MQ_HOST_KEY)
    mq_port = int(environ.get(config.MQ_PORT_KEY))
    mq_user = environ.get(config.MQ_USER_KEY)
    mq_pass = environ.get(config.MQ_PASS_KEY)

    return DownloaderConfig(
        input_queue_name=input_queue,
        output_queue_name=output_queue,
        headers=headers,
        verify_ssl=True,
        mq_host=mq_host,
        mq_port=mq_port,
        mq_user=mq_user,
        mq_pass=mq_pass
    )


class SecuritylabDownloader(Downloader):
    async def download_page(self, url: str) -> Optional[bytes]:
        if url.startswith(NEWS_URI):
            url = urljoin(f'https://{SECURITYLAB_DOMAIN}', url)
        try:
            return await self.http_get(url)
        except ClientError as e:
            logger.error(f'Undefined client error: {e.status_code}')
            return None
        except BadRequestError as e:
            logger.error(f'Bad request error: {e}')
            return None
        except ServerIsBeingUpdatedError as e:
            logger.error(f'ServerIsBeingUpdate error: {e}')
            return None
        except ServerError as e:
            logger.error(f'Server error: {e}')
            return None
        except NotFoundError as e:
            logger.error(f'Not found error: {e}')
            return None
        except DownloaderError as e:
            logger.error(f'Undefined downloader error: {e}')
            return None


async def main():
    cfg = init_downloader_cfg(HEADERS)
    downloader = SecuritylabDownloader(cfg)
    await downloader.run()


if __name__ == "__main__":
    logger.info('[+] Securitylab downloader started')
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', seconds=config.INTERVAL, id='seclab_downloader',
                      max_instances=config.MAX_INSTANCES)
    scheduler.start()
    asyncio.get_event_loop().run_forever()
