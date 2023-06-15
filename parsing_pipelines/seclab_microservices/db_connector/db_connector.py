from core.db_connector.db_connector import DatabaseConnector, DatabaseConnectorConfig
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from os import environ
from logging import getLogger


import config
import asyncio


logger = getLogger(__name__)
INDEX_NAME = 'seclab_microservices'


def init_db_connector_cfg() -> DatabaseConnectorConfig:
    db_url = environ.get(config.DB_URL_KEY)
    index_name = INDEX_NAME
    creds = (environ.get(config.CREDS_LOGIN_KEY, config.CREDS_PASS_KEY))
    input_queue = environ.get(config.INPUT_QUEUE_NAME_KEY)
    verify_certs = False
    mq_host = environ.get(config.MQ_HOST_KEY)
    mq_port = int(environ.get(config.MQ_PORT_KEY))
    mq_user = environ.get(config.MQ_USER_KEY)
    mq_pass = environ.get(config.MQ_PASS_KEY)
    return DatabaseConnectorConfig(
        db_url=db_url,
        index_name=index_name,
        creds=creds,
        input_queue_name=input_queue,
        verify_certs=verify_certs,
        mq_host=mq_host,
        mq_port=mq_port,
        mq_user=mq_user,
        mq_pass=mq_pass
    )


async def main():
    cfg = init_db_connector_cfg()
    db_connector = DatabaseConnector(cfg)
    await db_connector.run()


if __name__ == "__main__":
    logger.info('[+] Securitylab db connector started')
    scheduler = AsyncIOScheduler()
    scheduler.add_job(main, 'interval', seconds=config.INTERVAL, id='seclab_db_connector',
                      max_instances=config.MAX_INSTANCES)
    scheduler.start()
    asyncio.get_event_loop().run_forever()
