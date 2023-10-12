FROM jupyter/datascience-notebook:latest

RUN python3 -m pip install uvicorn fastapi -U -q

USER root

# Java Packages
RUN apt-get update
RUN apt-get install openjdk-11-jdk -y

# JavaScript Packages
RUN apt-get install nodejs npm jupyter -y
RUN npm install -g --unsafe-perm ijavascript
RUN ijsinstall --install=global

WORKDIR /code

# clone IJava Kernel
RUN wget https://github.com/SpencerPark/IJava/releases/download/v1.3.0/ijava-1.3.0.zip
RUN unzip ijava-1.3.0.zip && rm ijava-1.3.0.zip
RUN python3 install.py


COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install bash_kernel && python -m bash_kernel.install


COPY ./app /code/app

ENTRYPOINT ["python3", "/code/app/main.py"] 
