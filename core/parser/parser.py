import aio_pika
import json
import base64

from typing import List, Optional, Dict, Iterator, Callable
from bs4 import BeautifulSoup
from logging import getLogger
from datetime import datetime

logger = getLogger(__name__)


class IEntityModel:
    def serialize(self) -> Dict:
        raise NotImplementedError(f"{self.__class__.__name__}::serialize is not implemented")


class ParserConfig:
    def __init__(self,
                 input_queue_name: str,
                 output_queue_name: str,
                 downloader_queue: Optional[str],
                 mq_host: str,
                 mq_port: int,
                 mq_user: str,
                 mq_pass: str,
                 href_filter: Optional[Callable] = None
                 ):
        self.input_queue_name = input_queue_name
        self.output_queue_name = output_queue_name
        self.downloader_queue = downloader_queue
        self.mq_host = mq_host
        self.mq_port = mq_port
        self.mq_user = mq_user
        self.mq_pass = mq_pass
        self.href_filter = href_filter


def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError('Type %s not serializable' % type(obj))


class Parser:
    def __init__(self, parser_config: ParserConfig):
        self.config = parser_config

    async def extract_entities(self, html: str) -> List[IEntityModel]:
        raise NotImplementedError(f"{self.__class__.__name__}::extract_entity is not implemented")

    def extract_links(self, html: str) -> Iterator[str]:
        parser = BeautifulSoup(html, 'html.parser')
        for link in parser.find_all('a', href=True):
            if self.config.href_filter:
                yield self.config.href_filter(link.get('href'))

    async def run(self) -> None:
        try:
            mq_connection = await aio_pika.connect_robust(
                host=self.config.mq_host,
                port=self.config.mq_port,
                login=self.config.mq_user,
                password=self.config.mq_pass
            )
        except Exception as e:
            logger.critical(f'Attempt to connect to MQ failed: {e}')
            raise

        async with mq_connection:
            try:
                input_channel = await mq_connection.channel()
                input_queue = await input_channel.declare_queue(self.config.input_queue_name)
                output_channel = await mq_connection.channel()
                output_queue = await output_channel.declare_queue(self.config.output_queue_name)
                if self.config.downloader_queue:
                    downloader_channel = await mq_connection.channel()
                else:
                    downloader_channel = None
                if downloader_channel:
                    downloader_queue = await downloader_channel.declare_queue(self.config.downloader_queue)
                else:
                    downloader_queue = None

            except Exception as e:
                logger.critical(f'Unable to declare queue: {e}')
                raise
            message: aio_pika.abc.AbstractIncomingMessage
            async with input_queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        async with message.process():
                            msg_body = json.loads(message.body.decode('UTF-8'))
                            content = base64.b64decode(msg_body.get('content', '')).decode('UTF-8')
                            entities = await self.extract_entities(content)
                            for entity in entities:
                                serialized_entity = entity.serialize()
                                serialized_entity['source_url'] = msg_body.get('source_url')
                                await output_queue.channel.default_exchange.publish(
                                    aio_pika.Message(
                                        body=json.dumps(serialized_entity, default=json_serial).encode('UTF-8')),
                                    routing_key=output_queue.name
                                )
                            if downloader_queue:
                                for link in self.extract_links(content):
                                    if link and not link == msg_body.get('source_url'):
                                        await downloader_queue.channel.default_exchange.publish(
                                            aio_pika.Message(body=link.encode('UTF-8')),
                                            routing_key=downloader_queue.name
                                        )
                    except aio_pika.exceptions.MessageProcessError as e:
                        logger.error(f'Message processing failed: {e}')
