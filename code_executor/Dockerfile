FROM jupyter/base-notebook:latest
# FROM python:3.10-slim

USER root

RUN python3 -m pip install uvicorn fastapi -U -q

# Java Packages
RUN apt-get update
RUN apt-get install openjdk-11-jdk -y

# JavaScript Packages
RUN apt-get install nodejs npm jupyter -y
RUN npm install -g --unsafe-perm ijavascript
RUN ijsinstall --install=global

# clone IJava Kernel
RUN apt-get install unzip
RUN wget https://github.com/SpencerPark/IJava/releases/download/v1.3.0/ijava-1.3.0.zip
RUN unzip ijava-1.3.0.zip && rm ijava-1.3.0.zip
RUN python3 install.py


COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install bash_kernel && python -m bash_kernel.install

USER jovyan

WORKDIR /code
COPY ./app /code/app

ENTRYPOINT ["python3", "/code/app/main.py"] 
