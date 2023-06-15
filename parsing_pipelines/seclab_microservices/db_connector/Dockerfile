FROM python:3.8-slim-buster

WORKDIR /securitylab_db_connector

COPY core/db_connector/db_connector.py core/db_connector/db_connector.py
COPY core/db_connector/requirements.txt core_requirements.txt
COPY parsing_pipelines/seclab_microservices/db_connector/ .

RUN pip3 install -r core_requirements.txt
RUN pip3 install -r requirements.txt

CMD python3 db_connector.py
