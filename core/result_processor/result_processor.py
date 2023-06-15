import aio_pika
import json

from typing import Dict
from logging import getLogger


logger = getLogger(__name__)


class ResultProcessorConfig:
    def __init__(self,
                 input_queue_name: str,
                 output_queue_name: str,
                 mq_host: str,
                 mq_port: int,
                 mq_user: str,
                 mq_pass: str
                 ):
        self.input_queue_name = input_queue_name
        self.output_queue_name = output_queue_name
        self.mq_host = mq_host
        self.mq_port = mq_port
        self.mq_user = mq_user
        self.mq_pass = mq_pass


class ResultProcessor:
    def __init__(self, result_processor_config: ResultProcessorConfig):
        self.config = result_processor_config

    async def get_entity_id(self, entity: Dict) -> str:
        raise NotImplementedError(f'{self.__class__.__name__}::get_entity_id is not implemented')

    async def process_entity(self, entity: Dict) -> Dict:
        raise NotImplementedError(f'{self.__class__.__name__}::process_entity is not implemented')

    async def run(self):
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
            except Exception as e:
                logger.critical(f'Unable to declare queue: {e}')
                raise
            message: aio_pika.abc.AbstractIncomingMessage
            async with input_queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        async with message.process():
                            entity = json.loads(message.body.decode('UTF-8'))
                            entity_id = await self.get_entity_id(entity)
                            processed_entity = await self.process_entity(entity)
                            processed_entity['id'] = entity_id
                            await output_queue.channel.default_exchange.publish(
                                aio_pika.Message(body=json.dumps(processed_entity).encode('UTF-8')),
                                routing_key=output_queue.name
                            )
                    except aio_pika.exceptions.MessageProcessError as e:
                        logger.error(f'Message processing failed: {e}')
