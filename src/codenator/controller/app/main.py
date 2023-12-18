import argparse
import requests
import traceback
import json
import time
import os
import logging as logger
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
from conversation import Conversation
import boto3
from typing import Dict, Any
from utils import (
    get_model_type,
    get_model_metadata,
    get_languages,
    send_req_to_agent,
    security_scan_script,
    send_script_to_exc,
    extract_script,
    EncryptorClass,
    get_prompt_store,
    publish_metrics
)

app = FastAPI()

# health check
@app.get("/ping")
def ping():
    return {"Health_Check": "200"}

@app.get("/list_languages")
def list_languages():
    try:
        LANGUAGES = get_languages()
        return json.dumps(LANGUAGES)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return json.dumps({"error": e, "stacktrace": tb})
    
@app.post("/plan")
def plan(request: Dict[Any, Any]):
    start = time.perf_counter()
    try:
        params =request
        req_params = [
            "prompt",
            "model_family",
            "model_name",
            "language"
        ]
        for req_param in req_params:
            if req_param not in params:
                return {"error": f"Request must contain [{req_param}] parameter."}
        prompt = params.get("prompt")
        model_params = params.get("model_params", {})
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")
        model_type, can_stream = get_model_type(model_family, model_name)
        model_type = params.get("model_type", model_type)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        stream = params.get("stream", False)
        if stream:
            stream = can_stream

        LANGUAGES = get_languages()
        params = {
            "display_name": LANGUAGES[language]["display_name"],
            "tag_name": LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": LANGUAGES[language]["language_instructions"]
        }
    
        model_metadata = get_model_metadata(model_type)
        prompt_store = get_prompt_store()
        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                model_metadata["PLANNER_SYSTEM_PROMPT"],
                params
            ),
            language,
            model_family,
            model_name,
            model_metadata,
            model_params,
            ""
        )
        
        conv.history += prompt
        
        res = conv.send_to_agent(stream)
        if not res:
            raise
        if stream:            
            return StreamingResponse(
                res, 
                media_type="application/x-ndjson"
            )
        else:
            latency = int((time.perf_counter() - start) * 1000)
            publish_metrics(latency)
            return res
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

@app.post("/generate")
def generate(request: Dict[Any, Any]):
    start = time.perf_counter()
    try:
        params =request
        req_params = [
            "prompt",
            "model_family",
            "model_name",
            "language"
        ]
        for req_param in req_params:
            if req_param not in params:
                return {"error": f"Request must contain [{req_param}] parameter."}
        prompt = params.get("prompt")
        model_params = params.get("model_params", {})
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")
        model_type, can_stream = get_model_type(model_family, model_name)
        model_type = params.get("model_type", model_type)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        conv_id = params.get("conv_id", "")
        stream = params.get("stream", False)
        if stream:
            stream = can_stream

        LANGUAGES = get_languages()
        params = {
            "display_name": LANGUAGES[language]["display_name"],
            "tag_name": LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": LANGUAGES[language]["language_instructions"]
        }
    
        model_metadata = get_model_metadata(model_type)
        prompt_store = get_prompt_store()
        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                model_metadata["SYSTEM_PROMPT_TMPLT"],
                params
            ),
            language,
            model_family,
            model_name,
            model_metadata,
            model_params,
            conv_id
        )
        conv.append_chat(
            prompt_store.get_prompt_from_template(
                model_metadata["AGENT_REPLY_TMPLT"],
                params
            ),
            1
        )
        conv.append_chat(prompt)
        
        res = conv.send_to_agent(stream)
        if not res:
            raise
        if stream:            
            return StreamingResponse(
                res, 
                media_type="application/x-ndjson"
            )
        else:
            latency = int((time.perf_counter() - start) * 1000)
            publish_metrics(latency)
            return res
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

@app.post("/scan")
def scan(request: Dict[Any, Any]):
    
    def iter_func(scan_result, results=None):
        if results:
            for json_result in results:
                result = json.loads(json_result)
                result["vulnerabilities"] = scan_result
                yield json.dumps(result) + "\n"
        else:
            yield json.dumps(scan_result) + "\n"
            
    start = time.perf_counter()
    try:
        params = request
        req_params = [
            "script",
            "model_family",
            "model_name",
            "language",
            "conv_id"
        ]
        for req_param in req_params:
            if req_param not in params:
                return {"error": f"Request must contain [{req_param}] parameter."}
        script = params.get("script")
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")
        conv_id = params.get("conv_id")
        model_type, can_stream = get_model_type(model_family, model_name)
        model_type = params.get("model_type", model_type)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        model_params = params.get("model_params", {})
        scanner = params.get("scanner", "semgrep")
        stream = params.get("stream", False)
        if stream:
            stream = can_stream

        LANGUAGES = get_languages()
        params = {
            "display_name": LANGUAGES[language]["display_name"],
            "tag_name": LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": LANGUAGES[language]["language_instructions"]
        }
    
        model_metadata = get_model_metadata(model_type)
        prompt_store = get_prompt_store()
        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                model_metadata["SYSTEM_PROMPT_TMPLT"],
                params
            ),
            language,
            model_family,
            model_name,
            model_metadata,
            model_params,
            conv_id
        )

        res = conv.scan_script(script, scanner)
        if len(res["vulnerabilities"]) > 0:
            params["vulnerabilities"] = res["vulnerabilities"]
            conv.append_chat(
                prompt_store.get_prompt_from_template(
                    model_metadata["UNSECURE_SCRIPT_TMPLT"],
                    params
                )
            )
            ret = conv.send_to_agent(stream)
            if stream:
                return StreamingResponse(
                    iter_func(res, ret),
                    media_type="application/x-ndjson"
                )
            else:
                ret["vulnerabilities"] = res["vulnerabilities"]
                latency = int((time.perf_counter() - start) * 1000)
                publish_metrics(latency)
                return ret
        else:
            if stream:
                latency = int((time.perf_counter() - start) * 1000)
                publish_metrics(latency)
                return StreamingResponse(
                    iter_func(res),
                    media_type="application/x-ndjson"
                )
            else:
                latency = int((time.perf_counter() - start) * 1000)
                publish_metrics(latency)
                return res
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

@app.post("/execute")
def execute(request: Dict[Any, Any]):
    
    def iter_func(exec_result, results=None):
        start = time.perf_counter()
        if results:
            for json_result in results:
                result = json.loads(json_result)
                result["error"] = exec_result["error"]
                result["output"] = exec_result["output"]
                yield json.dumps(result) + "\n"
        else:
            yield json.dumps(exec_result) + "\n"
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
        
    start = time.perf_counter()
    try:
        params = request
        req_params = [
            "script",
            "model_family",
            "model_name",
            "language",
            "conv_id"
        ]
        for req_param in req_params:
            if req_param not in params:
                return {"error": f"Request must contain [{req_param}] parameter."}
        script = params.get("script")
        expected_output = params.get("expected_output", "")
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        language = params.get("language")
        conv_id = params.get("conv_id")
        model_type, can_stream = get_model_type(model_family, model_name)
        model_type = params.get("model_type", model_type)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        stream = params.get("stream", False)
        timeout = params.get("timeout")
        if stream:
            stream = can_stream
        model_params = params.get("model_params", {})

        LANGUAGES = get_languages()
        params = {
            "display_name": LANGUAGES[language]["display_name"],
            "tag_name": LANGUAGES[language]["tag_name"],
            "error_message": "",
            "script_output": "",
            "language_instructions": LANGUAGES[language]["language_instructions"]
        }

        model_metadata = get_model_metadata(model_type)
        prompt_store = get_prompt_store()
        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                model_metadata["SYSTEM_PROMPT_TMPLT"],
                params
            ),
            language,
            model_family,
            model_name,
            model_metadata,
            model_params,
            conv_id
        )
        res = conv.exec_script(script, expected_output, timeout)

        if res["error"]:
            params["error_message"] = res["output"]
            conv.append_chat(
                prompt_store.get_prompt_from_template(
                    model_metadata["SCRIPT_ERROR_TMPLT"],
                    params
                )
            )
            ret = conv.send_to_agent(stream)
            if stream:
                return StreamingResponse(
                    iter_func(res, ret),
                    media_type="application/x-ndjson"
                )
            else:
                ret["output"] = res["output"]
                ret["error"] = res["error"]
                latency = int((time.perf_counter() - start) * 1000)
                publish_metrics(latency)
                return ret
        else:
            if stream:
                return StreamingResponse(
                    iter_func(res),
                    media_type="application/x-ndjson"
                )
            else:
                latency = int((time.perf_counter() - start) * 1000)
                publish_metrics(latency)
                return res
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

@app.post("/save")
def save(request: Dict[Any, Any]):
    start = time.perf_counter()
    try:
        params =request
        req_params = [
            "script",
            "model_family",
            "model_name",
            "embedding_model_family",
            "embedding_model_name",
            "language"            
        ]
        for req_param in req_params:
            if req_param not in params:
                return {"error": f"Request must contain [{req_param}] parameter."}
        script = params.get("script")
        model_params = params.get("model_params", {})
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        embedding_model_params = params.get("embedding_model_params", {})
        embedding_model_family = params.get("embedding_model_family")
        embedding_model_name = params.get("embedding_model_name")
        language = params.get("language")
        model_type, can_stream = get_model_type(model_family, model_name)
        model_type = params.get("model_type", model_type)
        if model_type == "":
            return {"error": f"Unknown model!\nmodel_family: {model_family}, model_name: {model_name}"}
        LANGUAGES = get_languages()
        params = {
            "code": script,
            "language": LANGUAGES[language]["display_name"]
        }
        model_metadata = get_model_metadata(model_type)
        prompt_store = get_prompt_store()
        conv = Conversation(
            model_metadata["ROLES"], 
            prompt_store.get_prompt_from_template(
                "TASK_STORE_PROMPT",
                params
            ),
            language,
            model_family,
            model_name,
            model_metadata,
            model_params
        )
        
        res = conv.send_to_agent()
        if not res:
            raise
        embedding_model_params["prompt"] = json.loads(res["generated_text"])["body"]
        embedding_model_params["stream"] = False
        data = {
            "body": embedding_model_params, 
            "model_family": embedding_model_family, 
            "model_name": embedding_model_name
        }
        ret = requests.post(
            url=os.getenv("APP_API_LAYER_URL"), 
            data=json.dumps(data),
            stream=False
        )
        embedding = ret.json()["embedding"]
        url = f'{os.getenv("APP_TASK_STORE_URL")}/save_task'
        data = {
            "embedding": embedding,
            "script": script,
            "task_desc": embedding_model_params["prompt"],
            "language": LANGUAGES[language]["display_name"]
        }
        latency = int((time.perf_counter() - start) * 1000)
        publish_metrics(latency)
        return requests.post(url=url, data=json.dumps(data)).json()
        
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

@app.post("/load")
def load(request: Dict[Any, Any]):
    start = time.perf_counter()
    try:
        params =request
        req_params = [
            "prompt",
            "model_family",
            "model_name",
            "embedding_model_family",
            "embedding_model_name",
            "language"            
        ]
        for req_param in req_params:
            if req_param not in params:
                return {"error": f"Request must contain [{req_param}] parameter."}
        prompt = params.get("prompt")
        language = params.get("language")
        model_family = params.get("model_family")
        model_name = params.get("model_name")
        embedding_model_params = params.get("embedding_model_params", {})
        embedding_model_family = params.get("embedding_model_family")
        embedding_model_name = params.get("embedding_model_name")
        threshold = params.get("threshold", 0.5)
        limit = params.get("limit", 1)
        embedding_model_params["prompt"] = prompt
        embedding_model_params["stream"] = False
        model_type, can_stream = get_model_type(model_family, model_name)
        model_type = params.get("model_type", model_type)
        model_metadata = get_model_metadata(model_type)
        data = {
            "body": embedding_model_params, 
            "model_family": embedding_model_family, 
            "model_name": embedding_model_name
        }
        ret = requests.post(
            url=os.getenv("APP_API_LAYER_URL"),
            data=json.dumps(data),
            stream=False
        )
        embedding = ret.json()["embedding"]
        url = f'{os.getenv("APP_TASK_STORE_URL")}/load_task'
        data = {
            "embedding": embedding,
            "threshold": threshold,
            "limit": limit
        }
        matches = requests.post(url=url, data=json.dumps(data)).json()
        if len(matches) > 0:
            LANGUAGES = get_languages()
            params = {
                "display_name": LANGUAGES[language]["display_name"],
                "tag_name": LANGUAGES[language]["tag_name"],
                "error_message": "",
                "script_output": "",
                "language_instructions": LANGUAGES[language]["language_instructions"]
            }

            prompt_store = get_prompt_store()
            conv = Conversation(
                model_metadata["ROLES"], 
                prompt_store.get_prompt_from_template(
                    model_metadata["SYSTEM_PROMPT_TMPLT"],
                    params
                ),
                language,
                model_family,
                model_name,
                model_metadata,
                {}
            )
            conv.append_chat(
                prompt_store.get_prompt_from_template(
                    model_metadata["AGENT_REPLY_TMPLT"],
                    params
                ),
                1
            )
            conv.append_chat(prompt)
            conv.append_chat(
                f'Here is the code:\n```{params["tag_name"]}\n{matches[0]["code"]}\n```',
                1
            )
            latency = int((time.perf_counter() - start) * 1000)
            publish_metrics(latency)
            return {
                "matches": matches,
                "conv_id": conv.id
            }
        else:
            return {"matches": []}
        
    except Exception as e:
        # Handle any exceptions that occur during execution
        tb = traceback.format_exc()
        logger.error(f"Error {e}\StackTrace: {tb}")
        return {"error": str(e), "stacktrace": tb}

if __name__ == "__main__":  
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--api-layer-host", type=str, default="localhost")
    parser.add_argument("--api-layer-port", type=int, default=8080)
    parser.add_argument("--code-executor-host", type=str, default="localhost")
    parser.add_argument("--code-executor-port", type=int, default=8080)
    parser.add_argument("--code-scanner-host", type=str, default="localhost")
    parser.add_argument("--code-scanner-port", type=int, default=8080)
    parser.add_argument("--task-store-host", type=str, default="localhost")
    parser.add_argument("--task-store-port", type=int, default=8080)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--prompt-database-file", type=str, default="prompt/database.json")
    parser.add_argument("--prompt-store-name", type=str, default="")
    parser.add_argument("--kms", type=str)
    parser.add_argument("--models-metadata-db", type=str, default="")
    parser.add_argument("--models-metadata-file", type=str, default="config/model_meta.json")
    parser.add_argument("--languages-file", type=str, default="config/languages.json")
    parser.add_argument("--namespace", type=str, default="Codenator/controller/")
    parser.add_argument("--conv-bucket", type=str, default="")
    parser.add_argument("--conv-prefix", type=str, default="")
    args = parser.parse_args()
    logger.info(f"args: {args}")
    os.environ["APP_API_LAYER_URL"] = f"http://{args.api_layer_host}:{args.api_layer_port}/invoke"
    os.environ["APP_CODE_EXECUTOR_URL"] = f"http://{args.code_executor_host}:{args.code_executor_port}/execute_code"
    os.environ["APP_CODE_SCANNER_URL"] = f"http://{args.code_scanner_host}:{args.code_scanner_port}/scan"
    os.environ["APP_TASK_STORE_URL"] = f"http://{args.task_store_host}:{args.task_store_port}"
    os.environ["APP_PROMPT_STORE"] = args.prompt_store_name
    os.environ["APP_PROMPT_STORE_FILE"] = args.prompt_database_file
    os.environ["APP_MODELS_METADATA_FILE"] = args.models_metadata_file
    os.environ["APP_LANGUAGES_FILE"] = args.languages_file
    os.environ["APP_KMS_KEY"] = args.kms
    os.environ["APP_MODELS_METADATA_DB"] = args.models_metadata_db
    os.environ["CW_NAMESPACE"] = args.namespace
    os.environ["APP_CONV_BUCKET"] = args.conv_bucket
    os.environ["APP_CONV_KEY"] = args.conv_prefix
    
    uvicorn.run(
        "main:app", 
        host=args.host, 
        port=args.port,
        workers=args.workers,
        log_level="info"
    )
