FROM returntocorp/semgrep

COPY ./app /code/app
RUN mkdir -p /opt/ml/code
WORKDIR /code/app

RUN python3 -m pip install uvicorn fastapi -U -q
# RUN apk add cmake autoconf automake libtool binutils build-base elfutils-dev
# RUN python3 -m pip install --target "/code/app" awslambdaric -U -q

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


ENTRYPOINT ["python3", "/code/app/main.py"] 
# ENTRYPOINT ["python3", "-m", "awslambdaric"] 
# CMD [ "main.lambda_handler" ]