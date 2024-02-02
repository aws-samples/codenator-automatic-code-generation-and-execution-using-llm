FROM public.ecr.aws/docker/library/python:3.10-slim

WORKDIR /code/app
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
RUN mkdir -p /code/app/tmp

ENTRYPOINT ["python3", "/code/app/main.py"] 
