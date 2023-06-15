FROM python:3.8-slim-buster

WORKDIR /securitylab_result_processor

COPY core/result_processor/result_processor.py core/result_processor/result_processor.py
COPY core/result_processor/requirements.txt core_requirements.txt
COPY parsing_pipelines/seclab_microservices/result_processor/ .

RUN pip3 install -r core_requirements.txt
RUN pip3 install -r requirements.txt
RUN python3 -m spacy download ru_core_news_lg

CMD python3 ner_processor.py
