import httpx
import json
import aio_pika
import base64

from typing import Dict, Union, Optional
from logging import getLogger

logger = getLogger(__name__)

DEFAULT_TIMEOUT = 15


class DownloaderConfig:
    def __init__(self,
                 input_queue_name: str,
                 output_queue_name: str,
                 headers: Dict,
                 verify_ssl: bool,
                 mq_host: str,
                 mq_port: int,
                 mq_user: str,
                 mq_pass: str
                 ):
        self.input_queue_name = input_queue_name
        self.output_queue_name = output_queue_name
        self.headers = headers
        self.verify_ssl = verify_ssl
        self.mq_host = mq_host
        self.mq_port = mq_port
        self.mq_user = mq_user
        self.mq_pass = mq_pass


class Downloader:
    def __init__(self, downloader_config: DownloaderConfig):
        self.config = downloader_config

    async def http_get(self,
                       url: str,
                       params: Union[Dict, None] = None,
                       proxies: Union[Dict, None] = None
                       ) -> bytes:
        try:
            async with httpx.AsyncClient(verify=self.config.verify_ssl,
                                         timeout=DEFAULT_TIMEOUT, proxies=proxies) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.config.headers,
                )
                return self._handle_response(url, response)
        except httpx.ConnectTimeout:
            logger.error(f'HTTPX Connection timeout: {url}')
            raise ConnectionTimeout(url=url, status_code=-1)
        #TODO: PROXY ROUND ROBIN FOR THIS ERRORS

    @staticmethod
    def _handle_response(url: str, response: httpx.Response) -> bytes:
        kwargs = {'url': url, 'status_code': response.status_code}
        if response.status_code >= 500:
            raise ServerError(**kwargs)
        elif response.status_code == 423:
            raise ServerIsBeingUpdatedError(**kwargs)
        elif response.status_code == 404:
            raise NotFoundError(**kwargs)
        elif response.status_code == 400:
            raise BadRequestError(**kwargs)
        elif response.status_code != 200:
            raise ClientError(**kwargs)

        return response.content

    async def download_page(self, url: str) -> Optional[bytes]:
        raise NotImplementedError(f'{self.__class__.__name__}::download_page is not implemented')

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
            except Exception as e:
                logger.critical(f'Unable to declare queue: {e}')
                raise
            message: aio_pika.abc.AbstractIncomingMessage
            async with input_queue.iterator() as iterator:
                async for message in iterator:
                    try:
                        async with message.process():
                            url = message.body.decode('UTF-8')
                            downloaded_page = await self.download_page(url)
                            if downloaded_page:
                                result = {
                                    'source_url': url,
                                    'content': base64.b64encode(downloaded_page).decode('UTF-8')
                                }
                                await output_queue.channel.default_exchange.publish(
                                    aio_pika.Message(body=json.dumps(result).encode('UTF-8')),
                                    routing_key=output_queue.name
                                )
                    except aio_pika.exceptions.MessageProcessError as e:
                        logger.error(f'Message processing failed: {e}')


class DownloaderError(Exception):
    def __init__(self, url: str, status_code: int):
        self.url = url,
        self.status_code = status_code,


class ServerIsBeingUpdatedError(DownloaderError):
    TITLE = "Server is being updated"


class BadRequestError(DownloaderError):
    TITLE = "Bad request error"


class NotFoundError(DownloaderError):
    TITLE = "Not found error"


class ServerError(DownloaderError):
    TITLE = "Server error"


class ClientError(DownloaderError):
    TITLE = "Undefined client error"


class ConnectionTimeout(DownloaderError):
    TITLE = "Connection timeout"
