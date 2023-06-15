import aio_pika
import json

from elasticsearch import AsyncElasticsearch, ConflictError
from typing import Dict, Tuple
from logging import getLogger, INFO

logger = getLogger(__name__)
logger.setLevel(INFO)


class DatabaseConnectorConfig:
    def __init__(self,
                 db_url: str,
                 index_name: str,
                 creds: Tuple[str, str],
                 input_queue_name: str,
                 verify_certs: bool,
                 mq_host: str,
                 mq_port: int,
                 mq_user: str,
                 mq_pass: str
                 ):
        self.db_url = db_url
        self.index_name = index_name
        self.creds = creds
        self.input_queue_name = input_queue_name
        self.verify_certs = verify_certs
        self.mq_host = mq_host
        self.mq_port = mq_port
        self.mq_user = mq_user
        self.mq_pass = mq_pass


class DatabaseConnector:
    def __init__(self, database_connector_config: DatabaseConnectorConfig):
        self.config = database_connector_config

    async def create_document(self, document: Dict) -> None:
        try:
            async with AsyncElasticsearch(
                    hosts=[self.config.db_url],
                    basic_auth=self.config.creds,
                    verify_certs=self.config.verify_certs
            ) as db:
                await db.create(index=self.config.index_name,
                                id=document.get('id'),
                                document=document)
            logger.info('Document created')
        except ConflictError:
            logger.error(f'Trying to save a document whose id already exists')
        except Exception as e:
            logger.critical(f'Connection to Elasticsearch DB failed: {e}')

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
            except Exception as e:
                logger.critical(f'Unable to declare queue: {e}')
                raise

            message: aio_pika.abc.AbstractIncomingMessage
            async with input_queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        async with message.process():
                            document = json.loads(message.body.decode('UTF-8'))
                            await self.create_document(document)
                    except aio_pika.exceptions.MessageProcessError as e:
                        logger.error(f'Message processing failed: {e}')
