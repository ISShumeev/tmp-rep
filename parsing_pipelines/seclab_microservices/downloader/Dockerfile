FROM python:3.8-slim-buster

WORKDIR /securitylab_downloader

COPY core/downloader/downloader.py core/downloader/downloader.py
COPY core/downloader/requirements.txt core_requirements.txt
COPY parsing_pipelines/seclab_microservices/downloader/ .

RUN pip3 install -r core_requirements.txt
RUN pip3 install -r requirements.txt

CMD python3 downloader.py