from core.result_processor.result_processor import ResultProcessorConfig, ResultProcessor
from typing import Dict
from logging import getLogger
from os import environ
from apscheduler.schedulers.asyncio import AsyncIOScheduler


import hashlib
import config
import asyncio
import ru_core_news_lg


logger = getLogger(__name__)


def init_result_processor_cfg() -> ResultProcessorConfig:
    input_queue = environ.get(config.INPUT_QUEUE_NAME_KEY)
    output_queue = environ.get(config.OUTPUT_QUEUE_NAME_KEY)
    mq_host = environ.get(config.MQ_HOST_KEY)
    mq_port = int(environ.get(config.MQ_PORT_KEY))
    mq_user = environ.get(config.MQ_USER_KEY)
    mq_pass = environ.get(config.MQ_PASS_KEY)

    return ResultProcessorConfig(
        input_queue_name=input_queue,
        output_queue_name=output_queue,
        mq_host=mq_host,
        mq_port=mq_port,
        mq_user=mq_user,
        mq_pass=mq_pass
    )


class SecuritylabResultProcessor(ResultProcessor):
    def __init__(self, result_processor_config: ResultProcessorConfig):
        super().__init__(result_processor_config)
        self.nlp = ru_core_news_lg.load()

    async def get_entity_id(self, entity: Dict) -> str:
        title = entity.get('title', '')
        text = entity.get('text', '')
        entity_id = hashlib.sha1(
            f'{title}{text}'.encode('UTF-8')
        ).hexdigest()
        return entity_id

    async def process_entity(self, entity: Dict) -> Dict:
        document = self.nlp(entity.get('text', ''))
        organizations = []
        persons = []
        locations = []

        for named_entity in document.ents:
            if named_entity.label_ == 'ORG':
                organizations.append(str(named_entity))
            elif named_entity.label_ == 'PER':
                persons.append(str(named_entity))
            elif named_entity.label_ == 'LOC':
                locations.append(str(named_entity))

        entity['organizations'] = organizations
        entity['persons'] = persons
        entity['locations'] = locations
        return entity


async def main():
    cfg = init_result_processor_cfg()
    result_processor = SecuritylabResultProcessor(cfg)
    await result_processor.run()


if __name__ == "__main__":
    logger.info('[+] Securitylab result procesor started')
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', seconds=config.INTERVAL, id='seclab_processor',
                      max_instances=config.MAX_INSTANCES)
    scheduler.start()
    asyncio.get_event_loop().run_forever()
