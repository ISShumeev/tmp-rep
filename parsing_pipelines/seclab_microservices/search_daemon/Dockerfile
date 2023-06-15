FROM python:3.8-slim-buster

WORKDIR /securitylab_result_processor

COPY parsing_pipelines/seclab_microservices/search_daemon/ .

RUN pip3 install -r requirements.txt

CMD python3 stub_search_daemon.py
