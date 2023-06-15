
# Введение
За цель в данной работе было поставлено создание небольшой библиотеки (aka набора абстрактных классов), которая позволила бы достаточно быстро создавать системы поиска и анализа текстовой информации. В качестве демонстрации работоспособности данного решения была создана микросервисная система сбора и анализа информации с портала securitylab.ru. Эту же систему я хотел бы презентовать как итоговое домашнее задание.

# Описание архитектуры
Архитектуру проекта можно описать как пайплайн, состоящий из микросервисов, которые обмениваются данными через общую шину. Пайплайн состоит из следующих основных частей:
- Downloader
- Parser
- ResultProcessor
- DbConnector
- SearchDaemon (Optional)

Схематично проект можно описать следующим способом:
![image](https://github.com/ISShumeev/tmp-rep/assets/136640495/4f2ea4ad-ac1f-4c6b-9d9b-3f43da16a6de)

# Описание технологического стека
Core:
- RabbitMQ (via AioPika)
- Elasticsearch
- Python3


Parsing:
- HTTPX
- BeautifulSoup


Text processing:
- Scapy (NER с использованием корпуса текстов ru_core_news_lg)


# Сборка и запуск
```
$ mv .env.example .env
$ set -a
$ source .env
$ docker-compose config && docker-compose up -d && docker-compose logs -f
```

# Пример пайплайна
В качестве примера рабочего пайплайна была создана система парсинга новостного портала securitylab.ru (рабочий вариант - [http://можно-пожалуйста-4.рф](http://можно-пожалуйста-4.рф:5601/app/dashboards#/view/93053560-0a69-11ee-a15f-43008663521b?_g=(filters:!(),query:(language:kuery,query:''),refreshInterval:(pause:!t,value:0),time:(from:now-15M,to:now)))). В данном пайплайне в каждой статье выявляются такие сущности как организации, имена и локации, что, учитывая тематику новостного портала, может быть применимо на практике для выявления трендов упоминания той или иной группировки или ИБ организации, в том числе в контексте заданной локации. Например, по собранным данным был собран дашборд упоминания RaaS групп и локаций, что позволяет делать выводы об активности оных в (в т.ч. контексте интересующих стран):
![image](https://github.com/ISShumeev/tmp-rep/assets/136640495/25c17f17-3e83-409a-9810-e4fdb89bc5e1)
