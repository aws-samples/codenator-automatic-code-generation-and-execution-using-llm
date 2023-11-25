from importlib import import_module
import argparse
import json
import logging
from handlers import base
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import traceback
from typing import Dict, Any
import uvicorn
import boto3
import sys
import os
import time

global logger

logger = logging.getLogger(__name__)
log_level = logging.DEBUG if os.environ["APP_LOG_LEVEL"].upper() == "DEBUG" else logging.INFO
logger.setLevel(log_level)
logger.addHandler(logging.StreamHandler(sys.stdout))
app = FastAPI(title='api-layer')

def publish_metrics(latency) -> None:
    cw_client = boto3.client("cloudwatch")
    namespace = os.getenv("CW_NAMESPACE", "Codenator/api-layer/")
    logger.debug(f"Publishing CW metrics (Namespace: {namespace})")
    cw_client.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                'MetricName': "invocations",
                'Value': 1,
                'Unit': 'Count'
            },
            {
                'MetricName': "latency",
                'Value': latency,
                'Unit': 'Count'
            }
        ]
    )

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}


@app.get("/list_models")
def list_models():
    try:
        table_name = os.getenv("APP_TABLE_NAME", "")
        if table_name == "":
            all_models_file_path = "handlers/schemas/all-models.json"
            with open(all_models_file_path, "r") as all_models_file:
                all_models = json.load(all_models_file)
                return {"models": all_models}
        else:
            all_models = base.ddb_client.get_item(
                TableName=table_name,
                Key={
                    "pk": {
                        "S": "models"
                    },
                    "sk": {
                        "S": "all-models"
                    }
                }
            )["Item"]["models"]["S"]
            return {"models": json.loads(all_models)}
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        return {"error": f"An error occurred: {str(e)}", "stacktrace": tb }


@app.post("/invoke")
def invoke(request: Dict[Any, Any]):
    table_name = os.getenv("APP_TABLE_NAME", "")
    start = time.perf_counter()
    params = request
    req_params = [
        "model_family",
        "model_name"
    ]
    for req_param in req_params:
        if req_param not in params:
            return {"error": f"Request must contain [{req_param}] parameter."}
    model_family = params.get("model_family")
    model_name = params.get("model_name")
    body = params.get("body")
    try:
        invoke_model = import_module(
            "handlers." + model_family
        ).model(model_name, table_name).invoke
        ret = invoke_model(body)
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
        return ret

    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        return {"error": f"An error occurred: {str(e)}", "stacktrace": tb }


def invoke_with_response_stream(stream_response):
    try:
        for next_item in stream_response:
            # if "generated_text"  in next_item and next_item["generated_text"] != "<EOS_TOKEN>":
            yield json.dumps(next_item) + "\n"
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        yield json.dumps({"error": f"An error occurred: {str(e)}", "stacktrace": tb }) + "\n"


@app.post("/invoke_stream")
def invoke_stream(request: Dict[Any, Any]):
    table_name = os.getenv("APP_TABLE_NAME", "")
    start = time.perf_counter()
    params = request
    req_params = [
        "model_family",
        "model_name"
    ]
    for req_param in req_params:
        if req_param not in params:
            return {"error": f"Request must contain [{req_param}] parameter."}
    model_family = params.get("model_family")
    model_name = params.get("model_name")
    body = params.get("body")
    try:
        invoke_model = import_module(
            "handlers." + model_family
        ).model(model_name, table_name).invoke_with_response_stream
        ret = StreamingResponse(
            invoke_with_response_stream(
                invoke_model(body)
            ),
            media_type="application/x-ndjson"
        )
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
        return ret
    
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        return {"error": f"An error occurred: {str(e)}", "stacktrace": tb }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--table-name", type=str, default="")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--namespace", type=str, default="Codenator/api-layer/")
    args = parser.parse_args()
    os.environ["CW_NAMESPACE"] = args.namespace
    os.environ["APP_TABLE_NAME"] = args.table_name
    logger.info(f"args: {args}")
    uvicorn.run("main:app", host=args.host, port=args.port, workers=args.workers, log_level="info")