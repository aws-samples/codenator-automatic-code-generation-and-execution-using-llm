FROM returntocorp/semgrep

RUN python3 -m pip install uvicorn fastapi -U -q
WORKDIR /code/app
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
RUN mkdir -p /opt/ml/code

ENTRYPOINT ["python3", "/code/app/main.py"] 