import argparse
import json
import logging as logger
from fastapi import FastAPI, Request
import uvicorn
from typing import Dict, Any
import traceback
import time

app = FastAPI()
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

@app.post("/save")
def save(request: Dict[Any, Any]):
    start = time.perf_counter()
    params = request
    script = params.get("script")
    language = params.get("language")
    try:
        
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
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
    args = parser.parse_args()
    os.environ["CW_NAMESPACE"] = args.namespace
    logger.info(f"args: {args}")
    uvicorn.run(
        "main:app", 
        host=args.host, 
        port=args.port,
        log_level="info"
    )