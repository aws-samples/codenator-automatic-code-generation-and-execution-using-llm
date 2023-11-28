import argparse
import json
import logging as logger
from fastapi import FastAPI, Request
import uvicorn
from typing import Dict, Any
import traceback
import time
import boto3
import os
from store.opensearch import AOSSStore

app = FastAPI()

stores = {
    "aoss": AOSSStore
}

def publish_metrics(latency) -> None:
    cw_client = boto3.client("cloudwatch")
    namespace = os.getenv("CW_NAMESPACE", "Codenator/task-store/")
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

@app.post("/save_task")
def save_task(request: Dict[Any, Any]):
    start = time.perf_counter()
    params = request
    embedding = params.get("embedding")
    task_desc = params.get("task_desc")
    script = params.get("script", "")
    language = params.get("language")
    store_type = params.get("store_type", "aoss")
    try:
        store = stores[store_type]()
        if not store.save(embedding, task_desc, script, language):
            raise f"Saving task failed.\nembedding: {embedding}\nTask description: {task_desc}\nScript: {code}"
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
        return {"status": "saved"}
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\nStackTrace: {tb}")
        return {"status": "failed", "error": f"An error occurred: {str(e)}", "stacktrace": tb}

@app.post("/load_task")
def load_task(request: Dict[Any, Any]):
    start = time.perf_counter()
    params = request
    embedding = params.get("embedding")
    store_type = params.get("store_type", "aoss")
    similarity = params.get("similarity", "Cosine")
    threshold = params.get("threshold", 0.1)
    limit = params.get("limit", 1)
    try:
        store = stores[store_type](similarity)
        ret = store.search(embedding, threshold, limit)
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
        return ret
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\nStackTrace: {tb}")
        return {"error": f"An error occurred: {str(e)}", "stacktrace": tb}

@app.get("/aoss/list_tasks")
def list_tasks():
    store_type = "aoss"
    try:
        store = stores[store_type]()
        ret = store.list_tasks
        return ret
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\nStackTrace: {tb}")
        return {"error": f"An error occurred: {str(e)}", "stacktrace": tb}
    
if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--namespace", type=str, default="Codenator/task-store/")
    parser.add_argument("--aoss-endpoint", type=str, default="")
    parser.add_argument("--aoss-index", type=str, default="")
    args = parser.parse_args()
    os.environ["CW_NAMESPACE"] = args.namespace
    os.environ["AOSS_ENDPOINT"] = args.aoss_endpoint
    os.environ["AOSS_INDEX"] = args.aoss_index
    logger.info(f"args: {args}")
    uvicorn.run(
        "main:app", 
        host=args.host, 
        port=args.port,
        workers=args.workers,
        log_level="info"
    )