import aio_pika
import config
import asyncio

from os import environ
from logging import getLogger


logger = getLogger(__name__)

START_PAGE = 'https://www.securitylab.ru/news/page1_1.php'


async def main():
    downloader_queue = environ.get(config.DOWNLOADER_QUEUE)
    mq_host = environ.get(config.MQ_HOST_KEY)
    mq_port = int(environ.get(config.MQ_PORT_KEY))
    mq_user = environ.get(config.MQ_USER_KEY)
    mq_pass = environ.get(config.MQ_PASS_KEY)
    await asyncio.sleep(2 * config.INTERVAL)

    try:
        mq_connection = await aio_pika.connect_robust(
            host=mq_host,
            port=mq_port,
            login=mq_user,
            password=mq_pass
        )
    except Exception as e:
        logger.critical(e)
        return

    async with mq_connection:
        try:
            downloader_channel = await mq_connection.channel()
            downloader_queue = await downloader_channel.declare_queue(downloader_queue)
        except Exception as e:
            logger.critical(e)
            return
        await downloader_queue.channel.default_exchange.publish(
            aio_pika.Message(
                body=START_PAGE.encode('UTF-8')), routing_key=downloader_queue.name
        )

if __name__ == "__main__":
    asyncio.run(main())
