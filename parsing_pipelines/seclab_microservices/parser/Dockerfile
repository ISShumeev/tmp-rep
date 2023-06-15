FROM python:3.8-slim-buster

WORKDIR /securitylab_parser

COPY core/parser/parser.py core/parser/parser.py
COPY core/parser/requirements.txt core_requirements.txt
COPY parsing_pipelines/seclab_microservices/parser/ .

RUN pip3 install -r core_requirements.txt
RUN pip3 install -r requirements.txt

CMD python3 parser.py
